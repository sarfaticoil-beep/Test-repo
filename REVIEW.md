# Review of sarfati.co.il (November 2026)

The whole site was crawled: 138 Hebrew pages, 91 products with 103 weight options, and 12 blog posts.

## ⚠️ Needs your attention (business / legal)

1. **The kosher certificate on the site has expired.** The linked PDF (Badatz Eda Haredit, cert 68896) was valid until **31 March 2025**. It also says every listed product is **"NOT for Passover"**, but the site tags **73 products as "כשר לפסח"** and the kosher page says "all products on the site are kosher for Passover".
   → The new site shows **no Passover labels and no certificate PDF**. Send the current certificate and confirm the Passover status, and I'll add them back.
2. **Opening hours differ between pages.** The home page and deli page say Sun–Mon 10–16, Tue 9–18, Wed–Thu 9–20, Fri 8:30–14/15. The contact page says Sun–Tue 10–16, Wed 9–17, Thu 9–20, Fri 8–13/8:30–15.
   → The new site uses the **home page version** everywhere, stored in one place (`content/site.json`). Please confirm.
3. **Delivery days differ.** The home banner says "Wednesday Jerusalem, Thursday center". The delivery page has a more detailed schedule (Mon south every two weeks, Tue Sharon/Gush Dan, Wed Jerusalem, Thu Tel Aviv).
   → The new site uses the detailed schedule.
4. **The terms of use are outdated** (last updated April 2021). They list an old address (Beit Yosef, Hashmonaim 7), describe online card payment, and say the text is copyright of a law firm. A short ordering/delivery section was added on top, but **a lawyer should review them.**
5. **Customer club consent** named the web agency (גאו מדיה בע״מ) as a sender of marketing messages. The new form names only צרפתי מעושנים בע״מ.

## Problems found on the old site (all fixed in the new one)

**Speed and tech**
- The homepage HTML alone is 2.5 MB, built with WordPress, WooCommerce, Elementor, WPML and many plugins, three Facebook pixels and a reviews widget.
- Images were uploaded straight from phones (`WhatsApp-Image-…jpeg`, up to 2048px) without optimization.
- The new site is plain HTML with optimized WebP images and about 15 KB of JS, with no database or plugins to update or get hacked.

**Broken or sloppy content**
- The shop page shows the raw error text **"Template is not defined."**
- The contact page title contains the template placeholder **"% %"**.
- The gallery page is **empty**. The "satisfied customers" page has no content.
- Two product photos are missing on the server (404).
- The social share image (og:image) is a tiny maple-leaf icon, so shared links have no real preview.
- Typos: "בשן זית" (instead of "בשמן"), "סלומון", "שמנת, שמנת" in the menu, and "הליבות" alongside "הליבוט".
- One product name contradicts its options: "פורל עישון חם 1.800–2.500 ק״ג" is sold in 400–600 g options.
- Some variations have no price (₪0) and appear as selectable options.
- Three products have the same name: "מגש סלמון מעושן פרוס דק" (IDs 1621, 1567 and 1102), two of them at ₪469.
- "מארז ל2 צנצנות דגים מעושנים" costs **₪5**, which is probably a mistake.
- The English and French versions (`/en/`, `/fr/`) were poor machine translations ("French Fish" for Sarfati, "Cash" for kosher). They have been replaced by full hand translations, and Russian and Arabic were added.

**SEO and accessibility**
- Product pages had no structured data for prices. The new site adds `Product`, `Breadcrumb`, `LocalBusiness` (both branches with hours) and `BlogPosting` data for Google, plus a sitemap.
- **All old URLs are preserved:** products, categories, blog posts and pages, so rankings carry over. Retired URLs redirect.
- Accessibility: there was an accessibility statement but no real support behind it. The new site has a skip link, full keyboard navigation, labeled form fields, alt text, visible focus and reduced-motion support. The statement was rewritten (Israeli Standard 5568).

## What's new

- **New design** based on the brand colors (logo navy #3A5A99 and gold #C1912C), Frank Ruhl Libre and Assistant fonts, and mobile-first layout.
- **Shop**: category chips, live search, kosher filter, sorting, weight options with prices, out-of-stock handling, and "you may also like" suggestions.
- **Cart and checkout**:
  - Enforces the ₪350 delivery minimum and adds the ₪35 delivery fee.
  - Shows a progress bar toward free delivery over ₪550.
  - Offers home delivery, pickup at Shilat, or pickup at Sarona.
  - Includes a delivery-zone picker that shows each zone's day.
  - Sends the order to WhatsApp as a pre-filled message.
- **New pages**: "צרפתי לעסקים" (corporate platters and wholesale form), a full HTML version of the deli menu (it was only a JPG before), a real gallery, and a delivery FAQ.
- **One source of truth** for phone numbers, hours and shipping rules (`content/site.json`).

## What you lose by leaving WooCommerce

- **Online card payment.** Orders now arrive by WhatsApp, and you take payment when confirming (phone, Bit, or a payment link). This fits weighed products, whose price is only final after weighing. If you want card payment on the site later, options include a hosted payment link per order (e.g. Meshulam / Grow, PayPlus, Tranzila), or a hosted cart service such as Snipcart (paid).
- **Customer accounts and order history** (`/my-account/`).
- **Automatic stock management.** Stock is now updated by editing `products.json`.
