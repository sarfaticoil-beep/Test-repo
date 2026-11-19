# Sarfati – אתר צרפתי דגים מעושנים

A fast, static rebuild of [sarfati.co.il](https://www.sarfati.co.il) that can be hosted for free, in five languages: Hebrew (site root), English `/en/`, French `/fr/`, Russian `/ru/` and Arabic `/ar/`.
No WordPress, no plugins, no database. The build uses only the Python standard library.

## What's inside

| Path | What it is |
|---|---|
| `content/site.json` | **Business details in one place**: phones, WhatsApp, email, addresses, opening hours, delivery days, shipping rules. Change it here and every page updates. |
| `content/pages/<lang>/*.html` | Text of the regular pages in each language (home, story, deli & menu, events, delivery, kosher, business, press, gallery, contact, club, accessibility). |
| `content/i18n/<lang>.json` | Menu, button, cart and form texts in each language. |
| `content/i18n/products.<lang>.json` | Product names and descriptions in English, French, Russian and Arabic (prices and stock stay in `products.json`). |
| `assets/data/products.json` | The product catalogue (91 products: name, price, weight options, stock, categories, kosher, photos, description). |
| `assets/data/posts.json` | The 12 blog posts (Hebrew only). |
| `content/terms.txt` | Terms of use / privacy policy text. |
| `assets/` | CSS, JavaScript, optimized WebP images. |
| `tools/build.py` | Builds the site into `_site/`. |
| `REVIEW.md` | Review of the old site: what was wrong and what changed. |

## Build and preview locally

```bash
python3 tools/build.py
cd _site && python3 -m http.server 8000   # open http://localhost:8000
```

## Common edits

- **Change a price / mark out of stock:** edit `assets/data/products.json` (`price`, `inStock`, or a variant's `price`/`inStock`).
- **Change hours, phone, delivery days, minimum order, free-shipping threshold:** edit `content/site.json`.
- **Add a new product:** add it to `assets/data/products.json`, then add its name and description to each `content/i18n/products.<lang>.json` (the build stops if one is missing).
- **Add a product photo:** put a `.webp`/`.jpg` in `assets/img/p/` and add its path to the product's `images` list.

On GitHub you can edit these files straight in the browser. Each change to `main` redeploys the site automatically.

## How ordering works

Customers add products to a cart (saved in their browser), fill in their details and delivery method, and send the order **to the business WhatsApp (052-5199993)** as a pre-filled message. The cart enforces the ₪350 delivery minimum, adds the ₪35 delivery fee, and makes delivery free over ₪550. Staff confirm availability, final weight and payment with the customer, as many weighed products already required.

Forms (contact, events, club, business) also open WhatsApp. To get them by **email** instead, create a free [Web3Forms](https://web3forms.com) access key and set it in `content/site.json`:

```json
"formEndpoint": "https://api.web3forms.com/submit",
"formAccessKey": "YOUR-KEY"
```

Orders then also arrive by email, in addition to WhatsApp.

## Online card payment (Rivhit iCredit)

Card payment needs a small server function, `functions/api/checkout.js`, so it runs on **Cloudflare Pages** (free), not GitHub Pages.
The function recalculates every price from the catalogue (the browser cannot change prices), checks the delivery minimum and stock,
then asks iCredit for a secure payment page. Order details (items, address, delivery day, notes) go into the iCredit sale,
and a copy of every paid order is e-mailed to `ORDER_EMAIL`.

Set up once in Cloudflare Pages (Settings → Variables and secrets):

| Name | Value |
|---|---|
| `PAYMENTS` | `1` (build variable: shows the "Pay by card" button) |
| `ICREDIT_TOKEN` | **secret** – the iCredit payment page token (GroupPrivateToken) from Rivhit |
| `ICREDIT_SANDBOX` | `1` while testing with Rivhit's test token, `0` for real payments |
| `ICREDIT_SALE_TYPE` | `2` = J5 hold (charge the final amount after weighing), `1` = charge immediately |
| `ORDER_EMAIL` | the e-mail that receives a copy of every paid order |

Without `PAYMENTS=1` (e.g. on GitHub Pages) the site keeps sending orders by WhatsApp.

## Free hosting

**Option A – GitHub Pages (already set up):**
1. Merge this branch into `main`.
2. In the repository open *Settings → Pages* and set *Source* to **GitHub Actions**.
3. The workflow in `.github/workflows/deploy.yml` builds and publishes the site.
4. Custom domain: in *Settings → Pages*, enter `www.sarfati.co.il`. At your domain registrar, add a `CNAME` record from `www` to `<your-github-username>.github.io`, and the four `A` records for the bare domain that GitHub lists in its docs. Turn on *Enforce HTTPS*.

**Option B – Cloudflare Pages (free, needed for card payment):** connect the repository and set:
- Build command: `python3 tools/build.py`
- Output directory: `_site`
- Environment variables: see "Online card payment" above.

**Keep old links working:** product, category, blog and page URLs match the old WordPress addresses, so Google rankings and shared links carry over. Old pages that no longer exist (e.g. `/en/`, `/my-account/`) redirect to their closest replacement.

**Before switching the domain:** in Google Search Console, submit `https://www.sarfati.co.il/sitemap.xml` once the new site is live.
