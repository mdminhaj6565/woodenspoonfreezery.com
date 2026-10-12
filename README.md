# woodenspoonfreezery.com

Static website for **Wooden Spoon Boutique Freezery**, small-batch ice cream from Wellington, New Zealand.
The repository root is the web root. Every push to `main` is deployed to Hostinger by Git auto-deploy.

## How the site is built

```
_build/
  build.py            generator: pages, journal, sitemap.xml, feed.xml, robots.txt, .htaccess
  check.py            checker: run after every build (exit 1 = something to fix)
  profile.md          brand voice and facts we may / may not state
  entity-map.md       entities used for schema.org about/mentions
  SEO-AUDIT.md        audit report (Bangla)
  content/
    site.json         name, URL, navigation, GA4 id, socials
    flavours.json     current flavours, limited-edition archive, classics
    redirects.json    301 merges and 410 rules (written into .htaccess)
    pages/*.html      one file per page: <!--META {...} --> + body HTML
    new/*.html        journal articles, same format
  plan/
    CONTENT-CALENDAR.md, AUTOPILOT.md, GSC-PROGRESS.md
```

```bash
python3 _build/build.py     # needs Python 3.10+ with Pillow
python3 _build/check.py     # needs beautifulsoup4 + lxml
```

Rules: never change an existing URL or image path; merge duplicates with a 301 in `redirects.json`;
dates come from `dt.date.today()` and article META, never back-dated; no invented facts, reviews or prices.

Placeholders available in page bodies: `{{flavour_grid:signature+limited}}`, `{{flavour_cards:dairy-free}}`,
`{{flavour_detail:cookies-and-cream}}`, `{{melted_grid}}`, `{{classics}}`, `{{allergen_table}}`,
`{{ingredient_list}}`, `{{latest_posts:3}}`, `{{faq}}`, `{{social_links}}`, `{{img:path|alt}}`.

## Deploying on Hostinger

1. hPanel → Websites → Manage → Files → File Manager: download a backup zip of `public_html` first.
2. Hostinger's Git deploy needs an empty target folder, so after the backup, empty `public_html`.
3. hPanel → Websites → Manage → Advanced → GIT → Connect with GitHub → choose this repository,
   branch `main`, directory `public_html` (leave blank if it asks for a sub-folder) → Deploy.
4. Turn on **Auto Deployment**. From then on every push to `main` goes live within about a minute.
5. Force HTTPS in hPanel → Security → SSL (the `.htaccess` already sends www → non-www in one hop).

## বাংলায় সংক্ষেপে

- এই repo-র root-ই website-এর root। `main`-এ push করলেই Hostinger নিজে deploy করে (Auto Deployment চালু থাকলে)।
- প্রথমবার: hPanel থেকে `public_html`-এর backup zip নামিয়ে folder খালি করুন, তারপর Advanced → GIT → Connect with GitHub → এই repo, branch `main` → Deploy → Auto Deployment On।
- কিছু বদলাতে `_build/content/` এর ফাইল edit করে `python3 _build/build.py` আর `python3 _build/check.py` চালান, তারপর commit ও push।
- পুরোনো URL বা ছবির path বদলাবেন না; duplicate page মেশাতে `redirects.json`-এ 301 দিন।
- এটা public repo, তাই Search Console-এর সংখ্যা বা private note এখানে রাখবেন না; সেগুলো report doc-এ থাকে।
