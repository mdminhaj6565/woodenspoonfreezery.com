#!/usr/bin/env python3
"""Static site generator for woodenspoonfreezery.com.

Content lives in _build/content/:
  site.json        global settings (name, url, nav, GA4 id, socials)
  flavours.json    flavour data (current range, melted-away archive, classics)
  pages/*.html     one file per page: <!--META {json} --> + body HTML
  new/*.html       journal articles, same format
  redirects.json   301/410 rules written into .htaccess

Run:  python3 _build/build.py      (from the repo root or anywhere)
Then: python3 _build/check.py      (exit 1 = something to fix)
"""
import datetime as dt
import html
import json
import math
import re
import shutil
from pathlib import Path
from xml.sax.saxutils import escape as xesc

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "_build"
CONTENT = BUILD / "content"
SITE = json.loads((CONTENT / "site.json").read_text())
FLAV = json.loads((CONTENT / "flavours.json").read_text())
BASE = SITE["url"].rstrip("/")
TODAY = dt.date.today()
YEAR = TODAY.year
CSS_VER = None  # set after CSS hash


def esc(s):
    return html.escape(str(s), quote=True)


def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", s)


def words(s):
    return len(re.findall(r"[A-Za-z0-9'’-]+", strip_tags(s)))


def slugify(s):
    s = s.lower().replace("&", "and").replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def out_path(url):
    """'/' -> index.html, '/about/' -> about.html, '/blog/x/' -> blog/x.html"""
    u = url.strip("/")
    return ROOT / ("index.html" if not u else u + ".html")


def abs_url(url):
    return BASE + url


def read_doc(path):
    raw = path.read_text()
    m = re.match(r"\s*<!--META\s*(\{.*?\})\s*-->\s*", raw, re.S)
    if not m:
        raise SystemExit(f"{path}: missing <!--META {{...}} --> header")
    meta = json.loads(m.group(1))
    meta["body"] = raw[m.end():]
    meta["_file"] = path.name
    return meta


# ---------------------------------------------------------------- images
_dims = {}


def dims(src):
    p = ROOT / src.lstrip("/")
    if src not in _dims:
        try:
            with Image.open(p) as im:
                _dims[src] = im.size
        except Exception:
            return (0, 0)
    return _dims[src]


def optimised(src, max_w=900):
    """Return a web-friendly copy (WebP, <= max_w wide) for oversized images.
    Originals stay at their old paths so existing links and image search keep working."""
    p = ROOT / src.lstrip("/")
    if not p.exists():
        return src
    if p.stat().st_size <= 150_000 and dims(src)[0] <= max_w * 1.5:
        return src
    rel = Path("images/opt") / (Path(src).stem + f"-{max_w}.webp")
    dst = ROOT / rel
    if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(p) as im:
            im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
            if im.width > max_w:
                im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
            im.save(dst, "WEBP", quality=80, method=6)
    return str(rel)


def img(src, alt, cls="", eager=False, sizes=None, max_w=900):
    src = optimised(src, max_w)
    w, h = dims(src)
    a = [f'src="/{esc(src.lstrip("/"))}"', f'alt="{esc(alt)}"']
    if w:
        a += [f'width="{w}"', f'height="{h}"']
    a.append('loading="eager" fetchpriority="high"' if eager else 'loading="lazy"')
    a.append('decoding="async"')
    if cls:
        a.append(f'class="{cls}"')
    if sizes:
        a.append(f'sizes="{sizes}"')
    return "<img " + " ".join(a) + ">"


# ---------------------------------------------------------------- entities
def load_entities():
    ents = {}
    md = (BUILD / "entity-map.md").read_text()
    for line in md.splitlines():
        m = re.match(r"\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(https?://\S+?)\s*\|", line)
        if m:
            ents[m.group(1)] = {"@type": m.group(3).strip(), "name": m.group(2).strip(), "sameAs": m.group(4).strip()}
    return ents


ENTITIES = load_entities()


def entity_list(keys):
    out = []
    for k in keys or []:
        if k not in ENTITIES:
            raise SystemExit(f"entity '{k}' is not in _build/entity-map.md")
        out.append(ENTITIES[k])
    return out


# ---------------------------------------------------------------- schema
ORG_ID = BASE + "/#organization"


def org_schema():
    return {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": SITE["name"],
        "alternateName": ["Wooden Spoon Freezery", "Wooden Spoon"],
        "url": BASE + "/",
        "logo": {"@type": "ImageObject", "url": abs_url("/" + SITE["logo"]),
                 "width": SITE["logo_w"], "height": SITE["logo_h"]},
        "foundingDate": SITE["founded"],
        "foundingLocation": {"@type": "Place", "name": "Wellington, New Zealand"},
        "sameAs": list(SITE["social"].values()),
    }


def breadcrumb_schema(crumbs):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(u)}
            for i, (n, u) in enumerate(crumbs)
        ],
    }


def faq_schema(faq):
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q["q"],
             "acceptedAnswer": {"@type": "Answer", "text": strip_tags(q["a"]).strip()}}
            for q in faq
        ],
    }


# ---------------------------------------------------------------- flavour blocks
GROUP_LABEL = {
    "signature": "Signature",
    "limited": "Limited edition",
    "dairy-free": "Dairy-free",
    "classic": "Classic",
    "sandwich": "Ice cream sandwich",
}


def display_name(f):
    n = f["name"]
    if n.startswith("DF "):
        n = n[3:]
    return n


def flavours(group):
    if group == "all":
        return FLAV["current"]
    groups = group.split("+")
    return [f for f in FLAV["current"] if f["group"] in groups]


def flavour_grid(group):
    items = []
    for f in flavours(group):
        items.append(
            f'<li class="tile"><a href="/flavours-1/#{f["slug"]}">'
            f'{img(f["img"], display_name(f) + " ice cream tub", "tile-img")}'
            f'<span class="tile-name">{esc(display_name(f))}</span>'
            f'<span class="tile-tag">{esc(GROUP_LABEL[f["group"]])}</span></a></li>'
        )
    return '<ul class="tiles">' + "".join(items) + "</ul>"


ALLERGEN_WORDS = r"(?<!oat )(?<!coconut )\b(milk|cream|butter|whey)\b|\b(wheat|barley|soy|eggs?|egg whites|peanuts?|oats?|cashews?|hazelnuts?|almonds?|pistachios?)\b"


def bold_allergens(text):
    return re.sub(ALLERGEN_WORDS, lambda m: f"<strong>{m.group(0)}</strong>", esc(text), flags=re.I)


def allergens_of(f):
    txt = " ".join(f["ingredients"]).lower()
    desc = f["desc"].lower()
    dairy_free = f["group"] == "dairy-free"
    has = {
        "Milk": (not dairy_free) and bool(re.search(r"(?<!oat )(?<!coconut )\b(milk|cream|butter|whey)\b", txt)),
        "Gluten": "contains gluten" in desc or bool(re.search(r"\b(wheat|barley|malt)\b", txt)),
        "Oats": bool(re.search(r"\boats?\b", txt + " " + desc)),
        "Egg": bool(re.search(r"\begg", txt + " " + desc)),
        "Soy": bool(re.search(r"\bsoy", txt)),
        "Peanut": bool(re.search(r"peanut", txt + " " + desc)),
    }
    return has


def allergen_table(_=None):
    cols = ["Milk", "Gluten", "Oats", "Egg", "Soy", "Peanut"]
    rows = []
    for f in FLAV["current"]:
        a = allergens_of(f)
        cells = "".join(f'<td>{"Yes" if a[c] else "–"}</td>' for c in cols)
        rows.append(f'<tr><th scope="row"><a href="/flavours-1/#{f["slug"]}">{esc(display_name(f))}</a></th>{cells}</tr>')
    head = "".join(f'<th scope="col">{c}</th>' for c in cols)
    return (f'<div class="table-scroll"><table><caption class="small">Allergens in each flavour, from our most recently published '
            f'ingredient lists. “–” means not listed as an ingredient.</caption><thead><tr><th scope="col">Flavour</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def flavour_card(f, heading="h3"):
    ingr = "".join(f"<p>{bold_allergens(i)}</p>" for i in f["ingredients"])
    return (
        f'<article class="flavour" id="{f["slug"]}">'
        f'<div class="flavour-img">{img(f["img"], display_name(f) + " ice cream", "")}</div>'
        f'<div class="flavour-body"><span class="pill">{esc(GROUP_LABEL[f["group"]])}</span>'
        f'<{heading}>{esc(display_name(f))}</{heading}>'
        f'<p class="flavour-desc">{esc(f["desc"])}</p>'
        + (f'<details><summary>Ingredients &amp; allergens</summary>{ingr}'
           f'<p class="small">Allergens are shown in bold. Always check the label on your tub.</p></details>' if ingr else "")
        + "</div></article>"
    )


def flavour_cards(group):
    return '<div class="flavours">' + "".join(flavour_card(f) for f in flavours(group)) + "</div>"


def flavour_detail(slug):
    f = next(x for x in FLAV["current"] if x["slug"] == slug)
    return flavour_card(f, "h2")


def melted_grid():
    items = []
    for m in FLAV["melted"]:
        pic = img(m["img"], m["name"] + " limited edition ice cream", "tile-img") if m.get("img") else ""
        items.append(
            f'<li class="tile tile-static">{pic}<span class="tile-name">{esc(m["name"])}</span>'
            f'<span class="tile-tag">{esc(m["month"])}</span><span class="tile-desc">{esc(m["desc"])}</span></li>'
        )
    return '<ul class="tiles tiles-small">' + "".join(items) + "</ul>"


def classics():
    out = []
    for c in FLAV.get("classics", []):
        out.append(
            f'<article class="flavour" id="{slugify(c["name"])}">'
            f'<div class="flavour-img">{img(c["img"], c["name"] + " ice cream", "", max_w=600)}</div>'
            f'<div class="flavour-body"><h3>{esc(c["name"])}</h3><p class="flavour-desc">{c["desc"]}</p></div></article>'
        )
    return '<div class="flavours">' + "".join(out) + "</div>"


# ---------------------------------------------------------------- posts
POSTS = []


def load_posts():
    for p in sorted((CONTENT / "new").glob("*.html")):
        m = read_doc(p)
        m["url"] = f"/blog/{m['slug']}/"
        m.setdefault("updated", m["date"])
        m["wc"] = words(m["body"]) + sum(words(q["q"] + " " + q["a"]) for q in m.get("faq", []))
        POSTS.append(m)
    POSTS.sort(key=lambda x: (x["date"], x["_file"]), reverse=True)


def post_card(p, small=False):
    thumb = f"images/blog/{p['slug']}-thumb.jpg"
    return (
        f'<li class="post-card"><a href="{p["url"]}">{img(thumb, p["title"], "post-thumb")}'
        f'<span class="post-title">{esc(p["title"])}</span></a>'
        + ("" if small else f'<p>{esc(p["description"])}</p>')
        + f'<span class="post-meta">{fmt_date(p["date"])} · {math.ceil(p["wc"] / 220)} min read</span></li>'
    )


def latest_posts(n):
    return '<ul class="post-grid">' + "".join(post_card(p) for p in POSTS[: int(n)]) + "</ul>"


def related(post, n=3):
    labels = set(post.get("labels", []))
    scored = sorted(
        (p for p in POSTS if p["slug"] != post["slug"]),
        key=lambda p: (len(labels & set(p.get("labels", []))), p["date"]),
        reverse=True,
    )
    return scored[:n]


def fmt_date(d):
    return dt.date.fromisoformat(d).strftime("%-d %B %Y")


# ---------------------------------------------------------------- title cards
FONT_DIR = BUILD / "fonts"


def wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def title_card(post):
    """1200x630 OG image + 600x400 thumbnail in the brand colours (no photos needed)."""
    out_dir = ROOT / "images" / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)
    og, th = out_dir / f"{post['slug']}.jpg", out_dir / f"{post['slug']}-thumb.jpg"
    src = CONTENT / "new" / post["_file"]
    if og.exists() and th.exists() and og.stat().st_mtime >= src.stat().st_mtime:
        return
    palette = post.get("card", ["#E84020", "#FFF3E6"])
    for path, (W, H), size in ((og, (1200, 630), 64), (th, (600, 400), 40)):
        im = Image.new("RGB", (W, H), palette[1])
        d = ImageDraw.Draw(im)
        band = int(H * 0.16)
        d.rectangle([0, H - band, W, H], fill=palette[0])
        # playful scoop circles
        r = int(H * 0.22)
        d.ellipse([W - r * 2 - 30, -r // 2, W - 30, r * 3 // 2], fill="#F7C8A8")
        d.ellipse([W - r * 3, r // 3, W - r, r * 7 // 3], fill="#FBE0C8")
        f_title = ImageFont.truetype(str(FONT_DIR / "josefin-sans-latin-700-normal.ttf"), size)
        f_small = ImageFont.truetype(str(FONT_DIR / "josefin-sans-latin-700-normal.ttf"), int(size * 0.42))
        pad = int(W * 0.07)
        lines = wrap(d, post["card_title"] if post.get("card_title") else post["title"], f_title, W - pad * 2 - r)
        y = int(H * 0.2)
        for ln in lines[:4]:
            d.text((pad, y), ln, font=f_title, fill="#3B2A1E")
            y += int(size * 1.15)
        d.text((pad, H - band + band // 2), "WOODEN SPOON · JOURNAL", font=f_small, fill="#FFFFFF", anchor="lm")
        im.save(path, "JPEG", quality=86, optimize=True, progressive=True)


# ---------------------------------------------------------------- layout
def head(meta, canonical, og_image, schema):
    title = meta["title"]
    desc = meta["description"]
    robots = meta.get("robots", "index, follow, max-image-preview:large")
    og_w, og_h = dims(og_image)
    ld = json.dumps({"@context": "https://schema.org", "@graph": schema}, ensure_ascii=False, separators=(",", ":"))
    ld = ld.replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{SITE['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<meta name="msvalidate.01" content="{SITE['bing_verify']}">
<meta name="theme-color" content="#E84020">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE['short_name'])} Journal" href="{BASE}/feed.xml">
<link rel="preload" href="/assets/fonts/josefin-sans-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/nunito-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css?v={CSS_VER}">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:locale" content="{SITE['locale']}">
<meta property="og:type" content="{'article' if meta.get('_kind') == 'post' else 'website'}">
<meta property="og:title" content="{esc(meta.get('og_title', title))}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{abs_url('/' + og_image)}">
<meta property="og:image:width" content="{og_w}">
<meta property="og:image:height" content="{og_h}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(meta.get('og_title', title))}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{abs_url('/' + og_image)}">
<script async src="https://www.googletagmanager.com/gtag/js?id={SITE['ga4']}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{SITE['ga4']}');</script>
<script type="application/ld+json">{ld}</script>
</head>
"""


def header(current):
    links = []
    for name, url in SITE["nav"]:
        cur = ' aria-current="page"' if url == current else ""
        links.append(f'<li><a href="{url}"{cur}>{esc(name)}</a></li>')
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/" aria-label="{esc(SITE['name'])} home">{img(SITE['logo'], SITE['name'], 'logo', eager=True)}<span class="brand-tag">{esc(SITE['tagline'])}</span></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" class="site-nav" aria-label="Main"><ul>{''.join(links)}</ul></nav>
  </div>
</header>
"""


def breadcrumbs_html(crumbs):
    parts = []
    for i, (n, u) in enumerate(crumbs):
        if i == len(crumbs) - 1:
            parts.append(f'<li aria-current="page">{esc(n)}</li>')
        else:
            parts.append(f'<li><a href="{u}">{esc(n)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(parts)}</ol></nav>'


def social_links():
    return '<ul class="social">' + "".join(
        f'<li><a href="{u}" rel="noopener" target="_blank">{esc(n)}</a></li>' for n, u in SITE["social"].items()
    ) + "</ul>"


def footer():
    fl = "".join(f'<li><a href="{u}">{esc(n)}</a></li>' for n, u in SITE["footer"])
    return f"""<footer class="site-footer">
  <div class="wrap footer-grid">
    <div><p class="footer-brand">{esc(SITE['name'])}</p><p>Small-batch ice cream, made in {esc(SITE['city'])}, New Zealand since {SITE['founded']}.</p>{social_links()}</div>
    <div><p class="footer-h">Explore</p><ul class="footer-links">{fl}</ul></div>
    <div><p class="footer-h">Journal</p><ul class="footer-links">{''.join(f'<li><a href="{p["url"]}">{esc(p["title"])}</a></li>' for p in POSTS[:5])}</ul></div>
  </div>
  <p class="wrap copy">© {YEAR} Wooden Spoon - Boutique Freezery Limited · <a href="/privacy/">Privacy</a> · <a href="/privacy-1/">Terms</a></p>
</footer>
<script src="/assets/site.js?v={CSS_VER}" defer></script>
</body>
</html>
"""


def faq_html(faq, heading="Frequently asked questions"):
    if not faq:
        return ""
    items = "".join(f'<details class="faq-item"><summary>{esc(q["q"])}</summary><div><p>{q["a"]}</p></div></details>' for q in faq)
    return f'<section class="faq" id="faq"><h2>{esc(heading)}</h2>{items}</section>'


PLACEHOLDERS = {
    "flavour_grid": flavour_grid,
    "flavour_cards": flavour_cards,
    "flavour_detail": flavour_detail,
    "melted_grid": lambda _=None: melted_grid(),
    "classics": lambda _=None: classics(),
    "latest_posts": latest_posts,
    "social_links": lambda _=None: social_links(),
    "allergen_table": allergen_table,
    "ingredient_list": lambda _=None: "".join(
        f'<h3 id="{f["slug"]}">{esc(display_name(f))} <span class="pill">{esc(GROUP_LABEL[f["group"]])}</span></h3>'
        + "".join(f"<p>{bold_allergens(i)}</p>" for i in f["ingredients"])
        for f in FLAV["current"]
    ),
    "img": lambda arg: img(*arg.split("|", 1)),
    "img_eager": lambda arg: img(*arg.split("|", 1), eager=True),
}


def expand(body, meta):
    def rep(m):
        name, _, arg = m.group(1).partition(":")
        if name == "faq":
            return faq_html(meta.get("faq", []), meta.get("faq_heading", "Frequently asked questions"))
        return PLACEHOLDERS[name](arg) if arg else PLACEHOLDERS[name]()
    return re.sub(r"\{\{([a-z_]+(?::[^}]*)?)\}\}", rep, body)


def updated_note(meta):
    n = meta.get("update_note")
    if not n:
        return ""
    return f'<p class="update-note"><strong>Updated {dt.date.fromisoformat(meta["updated"]).strftime("%B %Y")}:</strong> {esc(n)}</p>'


# ---------------------------------------------------------------- page builders
SITEMAP = []  # (url, lastmod, [images])


def write(url, doc):
    p = out_path(url)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc)


def build_page(meta):
    url = meta["url"]
    canonical = abs_url(url)
    crumbs = meta.get("crumbs") or ([["Home", "/"]] + ([[meta["h1"], url]] if url != "/" else []))
    og_image = meta.get("image", "images/og-default.jpg")
    body = expand(meta["body"], meta)
    page_type = meta.get("schema_type", "WebPage")
    page = {
        "@type": page_type,
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": meta["title"],
        "description": meta["description"],
        "inLanguage": SITE["lang"],
        "isPartOf": {"@id": BASE + "/#website"},
        "publisher": {"@id": ORG_ID},
        "primaryImageOfPage": {"@type": "ImageObject", "url": abs_url("/" + og_image)},
        "dateModified": meta.get("updated", TODAY.isoformat()),
    }
    if meta.get("about"):
        page["about"] = entity_list(meta["about"])
    if meta.get("mentions"):
        page["mentions"] = entity_list(meta["mentions"])
    schema = [org_schema(), page]
    if url == "/":
        schema.append({"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": SITE["name"],
                       "inLanguage": SITE["lang"], "publisher": {"@id": ORG_ID}})
    else:
        schema.append(breadcrumb_schema(crumbs))
    if meta.get("itemlist"):
        fl = flavours(meta["itemlist"])
        page["mainEntity"] = {
            "@type": "ItemList",
            "numberOfItems": len(fl),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": display_name(f),
                 "url": abs_url(f"/flavours-1/#{f['slug']}"), "image": abs_url("/" + f["img"])}
                for i, f in enumerate(fl)
            ],
        }
    if meta.get("faq"):
        schema.append(faq_schema(meta["faq"]))
    crumbs_html = "" if url == "/" else breadcrumbs_html(crumbs)
    intro = f'<p class="lead">{meta["lead"]}</p>' if meta.get("lead") else ""
    hero = "" if meta.get("no_h1_block") else f'<div class="page-head wrap">{crumbs_html}<h1>{esc(meta["h1"])}</h1>{intro}{updated_note(meta)}</div>'
    doc = head(meta, canonical, og_image, schema) + header(url) + f'<main id="main">{hero}<div class="wrap content">{body}</div></main>' + footer()
    write(url, doc)
    if "noindex" not in meta.get("robots", ""):
        imgs = re.findall(r'<img src="(/[^"]+)"[^>]*alt="([^"]*)"', body)
        SITEMAP.append((url, meta.get("updated", TODAY.isoformat()), imgs[:30]))


def build_post(meta):
    url = meta["url"]
    canonical = abs_url(url)
    title_card(meta)
    og_image = f"images/blog/{meta['slug']}.jpg"
    crumbs = [["Home", "/"], ["Journal", "/blog/"], [meta["h1"], url]]
    body = expand(meta["body"], meta)
    post = {
        "@type": "BlogPosting",
        "@id": canonical + "#article",
        "headline": meta["h1"][:110],
        "description": meta["description"],
        "image": {"@type": "ImageObject", "url": abs_url("/" + og_image), "width": 1200, "height": 630},
        "datePublished": meta["date"],
        "dateModified": meta["updated"],
        "author": {"@type": "Organization", "name": SITE["author"], "url": abs_url("/about/")},
        "publisher": {"@id": ORG_ID},
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "inLanguage": SITE["lang"],
        "wordCount": meta["wc"],
        "articleSection": (meta.get("labels") or ["Journal"])[0],
        "keywords": ", ".join(meta.get("labels", [])),
    }
    if meta.get("about"):
        post["about"] = entity_list(meta["about"])
    if meta.get("mentions"):
        post["mentions"] = entity_list(meta["mentions"])
    schema = [org_schema(), post, breadcrumb_schema(crumbs)]
    if meta.get("faq"):
        schema.append(faq_schema(meta["faq"]))
    rel = related(meta)
    rel_html = '<section class="related"><h2>Keep reading</h2><ul class="post-grid">' + "".join(post_card(p, True) for p in rel) + "</ul></section>"
    upd = f' · Updated {fmt_date(meta["updated"])}' if meta["updated"] != meta["date"] else ""
    article = f"""<article class="post wrap-narrow">
{breadcrumbs_html(crumbs)}
<h1>{esc(meta['h1'])}</h1>
<p class="post-meta">By {esc(SITE['author'])} · {fmt_date(meta['date'])}{upd} · {math.ceil(meta['wc'] / 220)} min read</p>
{img(og_image, meta['title'], 'post-hero', eager=True)}
<div class="prose">{body}</div>
{faq_html(meta.get('faq', []))}
<aside class="author-box"><p><strong>About the author</strong></p><p>Written by the Wooden Spoon team. We've been making small-batch ice cream in {SITE['city']}, New Zealand since {SITE['founded']}. <a href="/about/">More about us</a> · <a href="/flavours-1/">See our flavours</a></p></aside>
{rel_html}
</article>"""
    meta["_kind"] = "post"
    doc = head(meta, canonical, og_image, schema) + header("/blog/") + f'<main id="main">{article}</main>' + footer()
    write(url, doc)
    SITEMAP.append((url, meta["updated"], [("/" + og_image, meta["title"])]))


def build_blog_index():
    meta = {
        "url": "/blog/",
        "title": "Ice Cream Journal: Tips & Guides | Wooden Spoon",
        "description": "Practical ice cream guides from a Wellington freezery: storing and softening ice cream, dairy-free options, allergens, parties, sandwiches and more.",
        "h1": "The Wooden Spoon Journal",
        "lead": "Guides, tips and flavour notes from our kitchen in Wellington: how to store, serve and enjoy ice cream at its best.",
        "updated": max((p["updated"] for p in POSTS), default=TODAY.isoformat()),
        "schema_type": "CollectionPage",
        "image": "images/og-default.jpg",
        "body": '<ul class="post-grid">' + "".join(post_card(p) for p in POSTS) + "</ul>",
    }
    build_page(meta)


def build_404():
    meta = {
        "url": "/404/",
        "title": "Page not found | Wooden Spoon Boutique Freezery",
        "description": "Sorry, that page has melted away. Try our flavours, FAQs or journal instead.",
        "h1": "This page has melted away",
        "robots": "noindex, follow",
        "body": '<p>Sorry, we couldn\'t find that page. It may have moved when we refreshed the site.</p>'
                '<ul class="link-list"><li><a href="/">Home</a></li><li><a href="/flavours-1/">Our flavours</a></li>'
                '<li><a href="/stockists/">Where to find us</a></li><li><a href="/blog/">Journal</a></li><li><a href="/questions/">FAQs</a></li></ul>',
    }
    build_page(meta)


# ---------------------------------------------------------------- site files
def write_sitemap():
    seen = set()
    rows = []
    for url, lastmod, imgs in sorted(SITEMAP, key=lambda x: (x[0] != "/", x[0])):
        if url in seen:
            continue
        seen.add(url)
        im = "".join(
            f"<image:image><image:loc>{xesc(abs_url(s))}</image:loc></image:image>"
            for s, _alt in dict.fromkeys(imgs)
        )
        rows.append(f"<url><loc>{xesc(abs_url(url))}</loc><lastmod>{lastmod}</lastmod>{im}</url>")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(rows) + "\n</urlset>\n"
    )


def write_robots():
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nDisallow: /_build/\nDisallow: /data/\n\n"
        f"Sitemap: {BASE}/sitemap.xml\n"
    )


def write_feed():
    items = []
    for p in POSTS[:20]:
        pub = dt.datetime.fromisoformat(p["date"] + "T09:00:00+13:00").strftime("%a, %d %b %Y %H:%M:%S %z")
        items.append(
            f"<item><title>{xesc(p['title'])}</title><link>{abs_url(p['url'])}</link>"
            f"<guid isPermaLink=\"true\">{abs_url(p['url'])}</guid><pubDate>{pub}</pubDate>"
            f"<description>{xesc(p['description'])}</description></item>"
        )
    (ROOT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f"<title>{xesc(SITE['short_name'])} Journal</title><link>{BASE}/blog/</link>"
        f"<atom:link href=\"{BASE}/feed.xml\" rel=\"self\" type=\"application/rss+xml\"/>"
        f"<description>Ice cream guides and flavour notes from {xesc(SITE['name'])}</description>"
        f"<language>en-nz</language>{''.join(items)}</channel></rss>\n"
    )


def write_manifest():
    (ROOT / "manifest.webmanifest").write_text(json.dumps({
        "name": SITE["name"], "short_name": SITE["short_name"], "start_url": "/", "display": "standalone",
        "background_color": "#FFFAF3", "theme_color": "#E84020",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, indent=2))


def write_htaccess():
    rules = json.loads((CONTENT / "redirects.json").read_text())
    host = BASE.split("//")[1]
    lines = [
        "# Generated by _build/build.py - edit _build/content/redirects.json instead",
        "Options -Indexes -MultiViews",
        "DirectorySlash Off",
        "ErrorDocument 404 /404.html",
        "ErrorDocument 410 /404.html",
        "",
        "<IfModule mod_rewrite.c>",
        "RewriteEngine On",
        "",
        "# Private build files are never served",
        "RewriteRule ^(_build|\\.git|data)(/|$) - [F,L,NC]",
        "",
        "# Gone for good (junk URLs from old platforms)",
    ]
    for pat in rules["gone"]:
        lines.append(f"RewriteRule {pat} - [G,L]")
    lines += ["", "# Old pages merged into one canonical page (one hop, straight to https + main host)"]
    for old, new in rules["moved"].items():
        lines.append(f"RewriteRule ^{re.escape(old.strip('/'))}/?$ https://{host}{new} [R=301,L,NC]")
    for pat, new in rules.get("moved_patterns", {}).items():
        lines.append(f"RewriteRule {pat} https://{host}{new} [R=301,L,NC]")
    lines += [
        "",
        "# index.html and .html requests -> clean URL with trailing slash",
        "RewriteCond %{THE_REQUEST} \\s/+index\\.html[\\s?] [NC]",
        f"RewriteRule ^index\\.html$ https://{host}/ [R=301,L]",
        "RewriteCond %{THE_REQUEST} \\s/+([^\\s?]+?)\\.html[\\s?] [NC]",
        "RewriteCond %1 !^404$",
        f"RewriteRule ^ https://{host}/%1/ [R=301,L]",
        "",
        "# www -> main host",
        f"RewriteCond %{{HTTP_HOST}} ^www\\.{re.escape(host)}$ [NC]",
        f"RewriteRule ^(.*)$ https://{host}/$1 [R=301,L]",
        "",
        "# Missing trailing slash on a page -> add it",
        "RewriteCond %{REQUEST_FILENAME}.html -f",
        f"RewriteRule ^(.+[^/])$ https://{host}/$1/ [R=301,L]",
        "RewriteCond %{DOCUMENT_ROOT}/$1.html -f",
        f"RewriteRule ^(.+[^/])$ https://{host}/$1/ [R=301,L]",
        "",
        "# Clean URL -> file.html (internal)",
        "RewriteCond %{DOCUMENT_ROOT}/$1.html -f",
        "RewriteRule ^(.+?)/$ $1.html [L]",
        "</IfModule>",
        "",
        "<IfModule mod_headers.c>",
        "<FilesMatch \"\\.(css|js|woff2|jpg|jpeg|png|webp|gif|ico|svg)$\">",
        "Header set Cache-Control \"public, max-age=2592000\"",
        "</FilesMatch>",
        "<FilesMatch \"\\.(html|xml)$\">",
        "Header set Cache-Control \"public, max-age=600\"",
        "</FilesMatch>",
        "Header always set X-Content-Type-Options \"nosniff\"",
        "Header always set Referrer-Policy \"strict-origin-when-cross-origin\"",
        "</IfModule>",
        "",
        "<IfModule mod_mime.c>",
        "AddType application/manifest+json .webmanifest",
        "AddType font/woff2 .woff2",
        "</IfModule>",
        "",
    ]
    (ROOT / ".htaccess").write_text("\n".join(lines))


def default_og():
    p = ROOT / "images" / "og-default.jpg"
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "#FFF3E6")
    logo = Image.open(ROOT / SITE["logo"]).convert("RGBA")
    scale = 760 / logo.width
    logo = logo.resize((760, int(logo.height * scale)), Image.LANCZOS)
    im.paste(logo, ((W - logo.width) // 2, 170), logo)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONT_DIR / "josefin-sans-latin-700-normal.ttf"), 40)
    d.text((W // 2, 430), "SMALL-BATCH ICE CREAM · WELLINGTON, NZ", font=f, fill="#3B2A1E", anchor="mm")
    d.rectangle([0, H - 60, W, H], fill="#E84020")
    im.save(p, "JPEG", quality=88, optimize=True)


def main():
    global CSS_VER
    import hashlib
    css = (ROOT / "assets" / "site.css").read_bytes() + (ROOT / "assets" / "site.js").read_bytes()
    CSS_VER = hashlib.md5(css).hexdigest()[:8]
    default_og()
    load_posts()
    for post in POSTS:
        title_card(post)
    for p in sorted((CONTENT / "pages").glob("*.html")):
        build_page(read_doc(p))
    for post in POSTS:
        build_post(post)
    build_blog_index()
    build_404()
    write_sitemap()
    write_robots()
    write_feed()
    write_manifest()
    write_htaccess()
    print(f"Built {len(list((CONTENT / 'pages').glob('*.html')))} pages, {len(POSTS)} posts, "
          f"{len(SITEMAP)} sitemap URLs on {TODAY.isoformat()}")


if __name__ == "__main__":
    main()
