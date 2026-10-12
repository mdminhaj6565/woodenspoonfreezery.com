# Autopilot runbook — woodenspoonfreezery.com

Used by scheduled tasks. Repo: `mdminhaj6565/woodenspoonfreezery.com` (public), branch `main`.
The repo root is the web root; Hostinger deploys every push to `main`. Owner speaks Bangla:
messages and report entries in Bangla (keep English technical terms); website content in NZ English.

Report doc (private, holds all Search Console numbers): see `GSC-PROGRESS.md` for the link.

## 0. Setup (every run)

1. If there is no local clone: `mcp__claude-code-remote__add_repo` (owner `mdminhaj6565`,
   repo `woodenspoonfreezery.com`, access `push`), clone as the tool says, then
   `mcp__claude-code-remote__register_repo_root` if available. `git pull --rebase`.
2. `pip install pillow beautifulsoup4 lxml --break-system-packages -q` if imports fail.
3. Read `_build/profile.md` (voice, facts we may and may not state) and `_build/entity-map.md`.
4. Load `SendUserMessage` early so the final message reaches the owner.

## A. Publish run (one article)

1. Today's date in Asia/Dhaka. If a file in `_build/content/new/` already has `"date"` = today, stop
   (one article per day maximum) and send a one-line message.
2. Open `_build/plan/CONTENT-CALENDAR.md`; take the `planned` row with the lowest `#`.
   Check its main keyword is not already covered by an existing page or post; if it is, mark the row
   `skipped (duplicate)` and take the next one.
3. Research facts with WebSearch/WebFetch. Every statistic or rule must come from a real page you opened,
   linked in the text. If you cannot verify something, leave it out.
4. Write `_build/content/new/NN-slug.html` (NN = next number) using the same `<!--META {...} -->` header as
   the existing files: `slug`, `title` (≤60 chars), `h1`, `description` (70–160 chars), `date` (today),
   `labels`, `card` (two colours), `about` / `mentions` (keys from entity-map.md; add rows there if needed,
   only with a Wikipedia link you opened), `faq` (3–4 questions, answers 40–60 words).
   Body: 1,100–1,500 words including FAQ; first paragraph answers the question; each H2 opens with a
   direct answer; at least one table or checklist; at least 3 internal links to existing pages/posts;
   safety notes where relevant (allergens, dry ice, hot sugar).
5. Never: invented stories, quotes, reviews, prices, test results or statistics; copied text; lyrics;
   drawings of known characters; current stockists/prices/hours/contact details (Live verification
   required — see profile.md); back-dating; the agency name.
6. Add 2–3 links to the new article from relevant existing pages or posts where it genuinely helps
   (edit their source files in `_build/content/`).
7. `python3 _build/build.py` then `python3 _build/check.py /blog/<slug>/`. Fix every PROBLEM.
8. Calendar: mark the row `published YYYY-MM-DD`, add the URL and word count in the Status cell.
   If fewer than 8 rows are `planned`, append 10 new topics (same columns; Why = reason without numbers;
   season-aware: Nov–Mar summer topics, Apr–May feijoa/autumn, Jun–Jul Matariki/winter warmers,
   Aug–Oct spring and party planning).
9. Commit `Add article: <title>` (plus the attribution lines the session requires) and `git push`.
10. Wait about 2 minutes, then check `https://woodenspoonfreezery.com/` and the new URL with WebFetch.
    If the homepage is blank, 403 or 404: `git revert` the commit, push, and report it.
    If the new URL is 404 but the homepage works, Hostinger may not be deploying yet: report it, don't revert.
11. Report doc (Claude Docs tools): add a top row to Changelog (date, "New article: <title>", commit link,
    problems) and set the article's Status in Content plan to published. Read each tab before editing.
12. SendUserMessage in Bangla: title, URL, word count, live-check result, next planned topic and date.

## B. Search Console run (Monday & Thursday, html-site-automation)

The recurring "HTML site SEO run (Mon & Thu)" task reads the Sites doc and handles this site when its row is
Active. GSC property: `https://woodenspoonfreezery.com/` (URL-prefix, non-www). Rules for this site:
- Public repo: no CSV or numbers in the repo; all numbers go in the report doc.
- At most 5 page updates and 2 new articles per run; prefer the next calendar topic for any gap query.
- Do not add redirects or change URLs in these runs; never block anything in robots.txt.
- Request indexing for new/changed URLs; stop after 3 "Oops! Something went wrong" in a row and list the rest
  under "Pending indexing" in `GSC-PROGRESS.md`.

## Rollback

`git revert <commit>` + `git push` restores the previous version within a minute or two.
