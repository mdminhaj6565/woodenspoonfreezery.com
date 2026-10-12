# woodenspoonfreezery.com — SEO audit ও rebuild report

তারিখ: ১২ অক্টোবর ২০২৬ · করেছে: Claude (seo-audit-final)
Search Console-এর সংখ্যা এই public repo-তে রাখা হয়নি; সেগুলো private report doc-এ আছে।

## ১. আগের অবস্থা (live site audit)

- Site-টা ছিল পুরোনো Squarespace site-এর archive কপি (২০১৫–২০২৪-এর বিভিন্ন snapshot জোড়া), Hostinger-এ static HTML হিসেবে।
- ৮৫টি URL sitemap-এ, যার মধ্যে `/api/...`, `/regform/...`, `/src/main/...` (404), cart, search, author ও gallery item-এর মত junk page।
- একই বিষয়ের একাধিক page: FAQ ৩টি, Contact ৩টি, Stockists ২টি, Trailer ২টি, Loyalty ২টি, About ২টি।
- প্রায় কোনো page-এ meta description নেই; canonical `http://`; অনেক page-এ খালি বা একাধিক H1; সব page-এর title একই ধাঁচের।
- পুরোনো তথ্য: "Online ordering is CLOSED until 01 February 2024", পুরোনো দাম, ২০১৮-এর giveaway, কাজ না করা cart ও Squarespace form।
- দুটি GA4 tag (আগের মালিকের G-9Q6H0QETRF ১৫টি page-এ + doubleclick iframe), Typekit ও মৃত Squarespace script।
- মাঝখানের এক মালিকের Filipino spam page (`/kapag-tamad-ka-nga-naman/`) index-এ ছিল।
- Spam/adult শব্দ, লুকানো link বা ক্ষতিকর বাইরের script পাওয়া যায়নি। Internal 404 শূন্য।
- Security issues ও Manual actions: কিছু নেই।

## ২. যা করা হয়েছে

- Python generator (`_build/build.py`) দিয়ে পুরো site নতুন করে: একটি CSS, ছোট JS, self-hosted font (Josefin Sans + Nunito Sans woff2), lazy image + width/height, একটি GA4 tag (G-P31YJFBZTY), Bing verification meta রাখা হয়েছে।
- সব জরুরি পুরোনো URL একই (trailing slash সহ, non-www, https); ছবির path একই।
- Duplicate ও junk page: ৪০টি 301 (এক hop-এ মূল page-এ) আর junk-এর জন্য 410। `.htaccess` Apache-এ পরীক্ষা করা।
- প্রতি page: আলাদা title (≤60) ও description (≤160), self canonical, OG/Twitter, একটি H1, breadcrumb, JSON-LD (Organization, WebPage/CollectionPage/AboutPage/ContactPage, BreadcrumbList, FAQPage, ItemList; article-এ BlogPosting + about/mentions)।
- Flavour page নতুন করে: ২৯টি বর্তমান flavour (ছবি, বর্ণনা, ingredients, bold allergen), allergen table, ৪৯টি পুরোনো limited edition-এর archive।
- Thin page-এ নতুন section ও FAQ: stockists, shop, trailer, contact, corporate, cookies-cream, cookie-sandwiches, superfood, our-process, questions।
- Loyalty, Privacy, Terms: `noindex, follow`।
- নতুন: `/blog/` journal ও ১৩টি article, sitemap.xml (আসল lastmod + image), robots.txt, feed.xml, 404.html, favicon set, manifest।
- `_build/check.py`: ভাঙা link/ছবি, H1, duplicate title/description, JSON-LD, article-এর শব্দসংখ্যা — এখন 0 problem।
- Desktop (1280px) ও mobile (390px) screenshot: কোথাও horizontal scroll নেই।

## ৩. নতুন article (প্রতিটি ১,০০০+ শব্দ, body + FAQ)

| # | URL | শব্দ |
| --- | --- | --- |
| 1 | /blog/how-to-store-ice-cream/ | 1,084 |
| 2 | /blog/how-to-soften-ice-cream/ | 1,078 |
| 3 | /blog/dairy-free-ice-cream-explained/ | 1,122 |
| 4 | /blog/gelato-vs-ice-cream/ | 1,105 |
| 5 | /blog/how-much-ice-cream-for-a-party/ | 1,059 |
| 6 | /blog/hokey-pokey-ice-cream/ | 1,086 |
| 7 | /blog/how-to-make-ice-cream-sandwiches/ | 1,062 |
| 8 | /blog/ice-cream-allergens-guide/ | 1,057 |
| 9 | /blog/wooden-ice-cream-spoons/ | 1,079 |
| 10 | /blog/keep-ice-cream-frozen-on-the-way-home/ | 1,050 |
| 11 | /blog/how-to-make-affogato/ | 1,063 |
| 12 | /blog/small-batch-ice-cream/ | 1,045 |
| 13 | /blog/office-ice-cream-party/ | 1,074 |

প্রতিটিতে যাচাই করা source (MPI/NZFSA freezer গাইড, FSANZ, Ministry for the Environment, Coeliac Australia, Cornell EHS, Wikipedia), table/checklist, FAQ ও ৪+ internal link। লেখক: The Wooden Spoon team।

## ৪. 54-checkpoint score

আগে আনুমানিক **36/100**, rebuild-এর পরে **90/100** (N/A ও Owner বাদ দিয়ে, weight High 3 / Medium 2 / Low 1)।
বাকি Partial: search intent ও competitor gap (SERP যাচাই বাকি), পুরোনো URL-এর নাম (`flavours-1`, `privacy-1`, `delivery-flavours`), Rich Results Test, ঠিকানা/ফোন, Bing Webmaster, https এক hop (deploy-এর পরে), নতুন page-এর indexing।

## ৫. Live verification required (owner দেবেন)

এগুলো যাচাই করা যায়নি, তাই site-এ রাখা হয়নি বা সাধারণভাবে লেখা হয়েছে:
- এখনকার stockist তালিকা, trailer-এর এবারের জায়গা ও সময়।
- Online ordering চালু কিনা, pack-এর দাম, delivery-র দিন ও এলাকা।
- Email, phone, ঠিকানা।
- Loyalty programme চালু কিনা।
- Ingredient/allergen list এখনও একই কিনা (২০২৪-এর শেষ প্রকাশিত label থেকে নেওয়া)।

## ৬. Owner-এর করণীয়

1. hPanel থেকে `public_html`-এর backup zip নামানো, folder খালি করা, তারপর Git → Connect with GitHub → এই repo, `main` → Auto Deployment On।
2. hPanel-এ Force HTTPS চালু।
3. উপরের "Live verification" তথ্য পাঠানো।
4. Bing Webmaster Tools-এ site যোগ (meta tag আগেই আছে)।
5. চাইলে repo Private করা (তাহলে GSC CSV-ও repo-তে রাখা যাবে)।
