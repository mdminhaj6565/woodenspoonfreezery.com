#!/usr/bin/env python3
"""Site checker. Run after build.py.  Exit code 1 = PROBLEMS to fix.

  python3 _build/check.py              # whole site
  python3 _build/check.py /blog/slug/  # site-wide checks + extra detail for these URLs

Checks: one H1, title <= 60 chars, description 70-160 chars, unique titles and
descriptions, canonical = own URL, valid JSON-LD, internal links and images
resolve (not to a redirect), img width/height, sitemap only lists indexable 200
pages, new journal articles 1,000-1,600 words.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "_build/content/site.json").read_text())
BASE = SITE["url"].rstrip("/")
REDIR = json.loads((ROOT / "_build/content/redirects.json").read_text())
MOVED = {k.rstrip("/") + "/" for k in REDIR["moved"]}

problems, warnings = [], []


def url_of(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "/"
    return "/" + rel[:-5] + "/"


def target_exists(u):
    u = u.split("#")[0].split("?")[0]
    if not u or u == "/":
        return (ROOT / "index.html").exists()
    p = ROOT / u.lstrip("/")
    if p.is_file():
        return True
    if u.endswith("/") and (ROOT / (u.strip("/") + ".html")).exists():
        return True
    return False


pages = [p for p in ROOT.rglob("*.html") if not any(part.startswith((".", "_")) or part == "node_modules" for part in p.relative_to(ROOT).parts)]
titles, descs = defaultdict(list), defaultdict(list)
noindex = set()
for p in sorted(pages):
    url = url_of(p)
    if url == "/404/":
        continue
    s = BeautifulSoup(p.read_text(), "lxml")
    h1 = s.find_all("h1")
    if len(h1) != 1:
        problems.append(f"{url}: {len(h1)} H1 tags")
    t = (s.title.string or "").strip() if s.title else ""
    if not t:
        problems.append(f"{url}: missing <title>")
    elif len(t) > 60:
        problems.append(f"{url}: title is {len(t)} chars (max 60): {t}")
    titles[t].append(url)
    d = s.find("meta", attrs={"name": "description"})
    d = d["content"].strip() if d else ""
    if not (70 <= len(d) <= 160):
        problems.append(f"{url}: meta description is {len(d)} chars (want 70-160)")
    descs[d].append(url)
    can = s.find("link", rel="canonical")
    if not can or can["href"] != BASE + url:
        problems.append(f"{url}: canonical is {can['href'] if can else 'missing'}")
    rob = s.find("meta", attrs={"name": "robots"})
    if rob and "noindex" in rob["content"]:
        noindex.add(url)
    for sc in s.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string)
            types = [g.get("@type") for g in data.get("@graph", [data])]
            if "Organization" not in types:
                warnings.append(f"{url}: no Organization in JSON-LD")
        except Exception as e:
            problems.append(f"{url}: invalid JSON-LD ({e})")
    for a in s.find_all("a", href=True):
        h = a["href"]
        if h.startswith(BASE):
            h = h[len(BASE):] or "/"
        if not h.startswith("/") or h.startswith("//"):
            continue
        path = h.split("#")[0].split("?")[0]
        if path.rstrip("/") + "/" in MOVED:
            problems.append(f"{url}: links to redirected URL {h}")
        elif not target_exists(path):
            problems.append(f"{url}: broken internal link {h}")
    for im in s.find_all("img"):
        src = im.get("src", "")
        if src.startswith("/") and not (ROOT / src.lstrip("/").split("?")[0]).exists():
            problems.append(f"{url}: missing image {src}")
        if not im.get("width") or not im.get("height"):
            problems.append(f"{url}: image without width/height {src}")
        if not im.get("alt"):
            warnings.append(f"{url}: image without alt {src}")
    if url.startswith("/blog/") and url != "/blog/":
        art = s.find("div", class_="prose")
        faq = s.find("section", class_="faq")
        text = (art.get_text(" ") if art else "") + " " + (faq.get_text(" ") if faq else "")
        n = len(re.findall(r"[A-Za-z0-9'’-]+", text))
        if not (1000 <= n <= 1600):
            problems.append(f"{url}: article has {n} words (want 1,000-1,600)")
        internal = [a["href"] for a in art.find_all("a", href=True) if a["href"].startswith("/")] if art else []
        if len(set(internal)) < 3:
            problems.append(f"{url}: only {len(set(internal))} internal links in the article body (want 3+)")
        if len(sys.argv) > 1 and url in sys.argv[1:]:
            print(f"{url}: {n} words, {len(set(internal))} internal links, title {len(t)} chars, description {len(d)} chars")

for t, urls in titles.items():
    if t and len(urls) > 1:
        problems.append(f"duplicate title on {urls}: {t}")
for d, urls in descs.items():
    if d and len(urls) > 1:
        problems.append(f"duplicate description on {urls}")

sm = (ROOT / "sitemap.xml").read_text()
for loc in re.findall(r"<url><loc>([^<]+)</loc>", sm):
    u = loc[len(BASE):] or "/"
    if not target_exists(u):
        problems.append(f"sitemap: {u} has no file")
    if u in noindex:
        problems.append(f"sitemap: {u} is noindex")
    if u in MOVED:
        problems.append(f"sitemap: {u} is a redirect")
for imgloc in re.findall(r"<image:loc>([^<]+)</image:loc>", sm):
    if not target_exists(imgloc[len(BASE):]):
        problems.append(f"sitemap image missing: {imgloc}")

for w in warnings:
    print("WARN   ", w)
for p in problems:
    print("PROBLEM", p)
print(f"\nChecked {len(pages)} HTML files: {len(problems)} problems, {len(warnings)} warnings")
sys.exit(1 if problems else 0)
