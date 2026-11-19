#!/usr/bin/env python3
"""Build the static, multilingual Sarfati website into ./_site

Usage:  python3 tools/build.py                       (output in _site/)
        BASE_PATH=/Test-repo python3 tools/build.py  (when served from a sub-folder)

Only the Python standard library is needed.
Languages: Hebrew at the site root, English /en/, French /fr/, Russian /ru/, Arabic /ar/.
Edit content in:
  content/site.json                    business details (phones, hours, shipping rules)
  content/i18n/<lang>.json             interface texts per language
  content/i18n/products.<lang>.json    product names and descriptions per language
  content/pages/<lang>/*.html          page texts per language
  assets/data/products.json            prices, stock, photos (shared by all languages)
  assets/data/posts.json               blog (Hebrew)
"""
import html
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")
# card payments need the Cloudflare Pages function (functions/api/checkout.js); turn on with PAYMENTS=1 at build time
PAYMENTS = os.environ.get("PAYMENTS", "0") == "1"
SITE = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
PRODUCTS = json.loads((ROOT / "assets/data/products.json").read_text(encoding="utf-8"))
POSTS = json.loads((ROOT / "assets/data/posts.json").read_text(encoding="utf-8"))
LANGS = ["he", "en", "fr", "ru", "ar"]
I18N = {l: json.loads((ROOT / f"content/i18n/{l}.json").read_text(encoding="utf-8")) for l in LANGS}
PTR = {l: json.loads((ROOT / f"content/i18n/products.{l}.json").read_text(encoding="utf-8")) for l in LANGS if l != "he"}
ASSET_VER = str(int(max(p.stat().st_mtime for p in (ROOT / "assets").rglob("*.*") if p.suffix in (".css", ".js"))))
TODAY = date.today().isoformat()
E = html.escape
SITEMAP = []

# current language while building (set by set_lang)
L = "he"
T = I18N["he"]


def set_lang(lang):
    global L, T
    L, T = lang, I18N[lang]


def ui(key, **kw):
    s = T["ui"][key]
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def u(path):
    """Site-absolute URL with optional base path."""
    return BASE + path


def money(n):
    return f"₪{n:,.0f}" if float(n).is_integer() else f"₪{n:,.2f}"


# ---------------------------------------------------------------- catalogue structure
CAT_KEYS = ["all", "smoked", "cold", "hot", "salads", "platters", "frozen", "fresh", "premium", "gifts", "drinks"]
CAT_HE_PATH = {
    "all": "/shop/", "smoked": "/product-category/דגים-מעושנים/",
    "cold": "/product-category/דגים-מעושנים/דגים-בעישון-קר/", "hot": "/product-category/דגים-מעושנים/דגים-בעישון-חם/",
    "salads": "/product-category/סלטי-דגים-מעושנים/", "platters": "/product-category/מגשים-לאירועים/",
    "frozen": "/product-category/דגים-קפואים/", "fresh": "/product-category/דגים-טריים/",
    "premium": "/product-category/מוצרים-מיוחדים-פרימיום/", "gifts": "/product-category/מתנות/",
    "drinks": "/product-category/אלכוהול/",
}
CAT_IMG = {"all": "cat-smoked", "smoked": "cat-smoked", "cold": "salmon-plate", "hot": "cat-hot-smoked", "salads": "cat-salads",
           "platters": "platter-rosettes", "frozen": "cat-frozen", "fresh": "cat-fresh", "premium": "products-collage",
           "gifts": "cat-gifts", "drinks": "cat-wine"}
KOSHER_KEYS = ["eda", "mehadrin", "beityosef"]
KOSHER_HE_PATH = {
    "eda": "/product-category/כשר-בדץ-העדה-החרדית/",
    "mehadrin": "/product-category/כשר-מהדרין-רבנות-חבל-מודיעין-הרהג-אהרן/",
    "beityosef": "/product-category/בדץ-בית-יוסף/",
}
FEATURED = [844, 699, 1127, 1120, 760, 1890, 875, 1562]

# content pages: id -> slug used for non-Hebrew languages (Hebrew paths come from content/pages/he/*.html)
PAGE_SLUG = {"home": "", "story": "our-story", "deli": "deli", "events": "events", "delivery": "delivery", "wolt": "wolt",
             "kosher": "kosher", "business": "business", "press": "press", "gallery": "gallery", "contact": "contact",
             "club": "club", "accessibility": "accessibility"}
HE_PAGE_PATH = {}

# old WordPress URLs that no longer have their own page -> new location
REDIRECTS = {
    "/product-category/אלכוהול/יינות/": "/product-category/אלכוהול/",
    "/product-category/אלכוהול/קוקטיילים-עם-ערק/": "/product-category/אלכוהול/",
    "/product-category/דגים-טריים/פילטים/": "/product-category/דגים-טריים/",
    "/product-category/הכל/": "/shop/",
    "/product-category/פורים/": "/shop/",
    "/product-category/פלטת-דגים-מעושנים/": "/product-category/מגשים-לאירועים/",
    "/product-category/כשר-לפסח-בדץ-בית-יוסף/": "/כשרות/",
    "/product-tag/כשר-לפסח/": "/כשרות/",
    "/product/מארז-מושלם-כשר-לפסח/": "/product/מארז-מושלם/",
    "/product/מארז-גורמה-כשר-לפסח/": "/product/מארז-גורמה/",
    "/category/דגים/": "/בלוג/",
    "/לקוחות-מרוצים/": "/כתבו-עלינו/",
    "/טופס-השארת-פרטים/": "/עסקים/",
    "/my-account/": "/cart/",
    "/checkout/": "/cart/",
}


def lpath(kind, key=None, lang=None):
    """Path of a page in a language (default: current)."""
    lang = lang or L
    if lang == "he":
        return {"page": lambda: HE_PAGE_PATH[key], "shop": lambda: "/shop/", "cat": lambda: CAT_HE_PATH[key],
                "product": lambda: f"/product/{key['slug']}/", "cart": lambda: "/cart/", "terms": lambda: "/תקנון/",
                "blog": lambda: "/בלוג/"}[kind]()
    pre = f"/{lang}"
    return {"page": lambda: f"{pre}/{PAGE_SLUG[key]}/".replace("//", "/"), "shop": lambda: f"{pre}/shop/",
            "cat": lambda: f"{pre}/shop/" if key == "all" else f"{pre}/shop/{key}/",
            "product": lambda: f"{pre}/product/{key['id']}/", "cart": lambda: f"{pre}/cart/",
            "terms": lambda: f"{pre}/terms/", "blog": lambda: f"{pre}/"}[kind]()


def alts(kind, key=None):
    return {l: lpath(kind, key, l) for l in LANGS}


# ---------------------------------------------------------------- localized data
def pname(p):
    return p["name"] if L == "he" else PTR[L][str(p["id"])][0]


def pdesc(p):
    return p["description"] if L == "he" else PTR[L][str(p["id"])][1]


def psummary(p):
    if L == "he":
        return p["summary"]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", pdesc(p))).strip()[:200]


def vlabel(label):
    if L == "he":
        return label
    for he, tr in T["units"].items():
        label = label.replace(he, tr)
    return re.sub(r"\((\d+)(?=\D)", r"(\1 ", label)


def cat(key):
    return T["cats"][key]  # [menu label, page title, intro]


def kosher_name(k):
    return T["kosher"][k]


def branch(bid):
    b = next(b for b in SITE["branches"] if b["id"] == bid)
    return {**b, **T["branches"][bid]}


# ---------------------------------------------------------------- html helpers
def img_tag(src, alt, w=None, h=None, cls="", lazy=True):
    attrs = [f'src="{u("/" + src.lstrip("/"))}"', f'alt="{E(alt)}"']
    if w:
        attrs.append(f'width="{w}" height="{h}"')
    if lazy:
        attrs.append('loading="lazy" decoding="async"')
    if cls:
        attrs.append(f'class="{cls}"')
    return f"<img {' '.join(attrs)}>"


def site_img(name, alt, **kw):
    return img_tag(f"assets/img/site/{name}.webp", alt, **kw)


def price_html(p):
    if p.get("variants"):
        return f'<span class="price-now">{E(ui("from", p=money(p["price"])))}</span>'
    return f'<span class="price-now">{money(p["price"])}</span>'


def product_card(p, order=0):
    img = p["images"][0] if p["images"] else "assets/img/fish-512.png"
    url = u(lpath("product", p))
    name = pname(p)
    out = "" if p["inStock"] else f'<span class="badge badge--out">{E(ui("outOfStock"))}</span>'
    if not p["inStock"]:
        action = f'<a class="btn btn--ghost btn--sm" href="{url}">{E(ui("details"))}</a>'
    elif p.get("variants"):
        action = f'<a class="btn btn--ghost btn--sm" href="{url}">{E(ui("chooseWeight"))}</a>'
    else:
        action = (f'<button type="button" class="btn btn--primary btn--sm" data-add="{p["id"]}" data-name="{E(name)}" data-he="{E(p["name"])}" '
                  f'data-price="{p["price"]}" data-image="{u("/" + img)}" data-url="{url}">{E(ui("addToCart"))}</button>')
    kosher = " ".join(p["kosher"])
    search = E((name + " " + psummary(p) + " " + p["name"]).lower())
    badges = "".join(f'<span class="badge">{E(kosher_name(k))}</span>' for k in p["kosher"] if k in KOSHER_KEYS)
    return f"""<article class="p-card{'' if p['inStock'] else ' is-out'}" data-price="{p['price']}" data-name="{E(name)}" data-order="{order}" data-kosher="{kosher}" data-search="{search}">
  {out}<a class="p-img" href="{url}" tabindex="-1" aria-hidden="true">{img_tag(img, name, 600, 600)}</a>
  <div class="p-body">
    <h3><a href="{url}">{E(name)}</a></h3>
    <div class="badges">{badges}</div>
    <div class="p-price">{price_html(p)}</div>
    <div class="p-actions">{action}</div>
  </div>
</article>"""


def sorted_products(items):
    return sorted(items, key=lambda p: not p["inStock"])


ICON = {
    "cart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    "truck": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h11v10H3zM14 9h4l3 3v4h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/></svg>',
    "snow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 2v20M4 6l16 12M20 6L4 18M9 3l3 3 3-3M9 21l3-3 3 3"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/></svg>',
    "wa": '<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true"><path d="M16 3a13 13 0 0 0-11.2 19.6L3 29l6.6-1.7A13 13 0 1 0 16 3zm0 23.7a10.7 10.7 0 0 1-5.5-1.5l-.4-.2-3.9 1 1-3.8-.2-.4A10.7 10.7 0 1 1 16 26.7zm5.9-8c-.3-.2-1.9-1-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7 0a8.8 8.8 0 0 1-4.4-3.8c-.3-.6.3-.5 1-1.7.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6a1.2 1.2 0 0 0-.9.4 3.7 3.7 0 0 0-1.1 2.7 6.5 6.5 0 0 0 1.3 3.4 14.7 14.7 0 0 0 5.7 5c2.1.9 2.9 1 4 .8a3.4 3.4 0 0 0 2.2-1.6 2.8 2.8 0 0 0 .2-1.6c-.1-.2-.3-.3-.6-.4z"/></svg>',
    "ig": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    "fb": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-7.5H16l.4-3h-2.9V8.6c0-.9.3-1.5 1.5-1.5h1.5V4.4a20 20 0 0 0-2.3-.1c-2.3 0-3.8 1.4-3.8 3.9v2.3H8v3h2.4V21z"/></svg>',
}

# ---------------------------------------------------------------- layout
def nav_items():
    deli_sub = [(ui("deliMenu"), lpath("page", "deli")), (ui("events"), lpath("page", "events")), (ui("gallery"), lpath("page", "gallery"))]
    deliv_sub = [(ui("deliveryZones"), lpath("page", "delivery")), (ui("wolt"), lpath("page", "wolt"))]
    items = [
        (ui("story"), lpath("page", "story"), None),
        (ui("shop"), lpath("shop"), [(cat(k)[0], lpath("cat", k)) for k in CAT_KEYS]),
        (ui("deli"), lpath("page", "deli"), deli_sub),
        (ui("delivery"), lpath("page", "delivery"), deliv_sub),
        (ui("business"), lpath("page", "business"), None),
        (ui("kosher"), lpath("page", "kosher"), None),
    ]
    if L == "he":
        items.append((ui("blog"), lpath("blog"), None))
    items.append((ui("contact"), lpath("page", "contact"), None))
    return items


def lang_switch(alt):
    cur = ' aria-current="true"'
    links = "".join(
        f'<li><a href="{u(alt.get(l) or lpath("page", "home", l))}" hreflang="{l}" lang="{l}"{cur if l == L else ""}>{E(I18N[l]["native"])}</a></li>'
        for l in LANGS)
    return f"""<details class="lang-switch"><summary aria-label="{E(ui('language'))}">{ICON['globe']}<span>{L.upper()}</span></summary><ul>{links}</ul></details>"""


def header(active, alt):
    items = []
    for label, path, sub in nav_items():
        cur = ' aria-current="page"' if active == path else ""
        if sub:
            subs = "".join(f'<li><a href="{u(p)}">{E(l)}</a></li>' for l, p in sub)
            items.append(f'<li><button type="button" class="nav-parent" aria-haspopup="true">{E(label)}</button><ul class="sub">{subs}</ul></li>')
        else:
            items.append(f'<li><a href="{u(path)}"{cur}>{E(label)}</a></li>')
    drawer_links = []
    for label, path, sub in nav_items():
        drawer_links.append(f'<a href="{u(path)}">{E(label)}</a>')
        if sub:
            drawer_links.append('<div class="sub-links">' + "".join(f'<a href="{u(p)}">{E(l)}</a>' for l, p in sub if p != path) + "</div>")
    drawer_langs = " · ".join(f'<a href="{u(alt.get(l) or lpath("page", "home", l))}" lang="{l}">{E(I18N[l]["native"])}</a>' for l in LANGS if l != L)
    s = SITE["shipping"]
    home = lpath("page", "home")
    return f"""<a class="skip-link" href="#main">{E(ui('skip'))}</a>
<div class="topbar">{E(ui('topbar', free=money(s['freeOver'])))} <a href="{u(lpath('page', 'delivery'))}">{E(ui('topbarLink'))}</a></div>
<header class="site-header">
  <div class="wrap header-inner">
    <button type="button" class="icon-btn menu-toggle" aria-label="{E(ui('menuOpen'))}" aria-expanded="false" aria-controls="drawer">{ICON['menu']}</button>
    <a class="brand" href="{u(home)}" aria-label="{E(ui('homeAria'))}"><img src="{u('/assets/img/logo.png')}" alt="Sarfati Premium Smokehouse" width="90" height="50"></a>
    <nav class="nav" aria-label="{E(ui('mainNav'))}"><ul>{''.join(items)}</ul></nav>
    <div class="header-actions">
      <a class="header-phone" href="tel:{SITE['phoneIntl']}" dir="ltr">{SITE['phone']}</a>
      {lang_switch(alt)}
      <a class="icon-btn" href="{u(lpath('cart'))}" aria-label="{E(ui('cart'))}">{ICON['cart']}<span class="cart-count" data-count="0" aria-live="polite">0</span></a>
    </div>
  </div>
</header>
<div class="drawer" id="drawer" aria-hidden="true">
  <div class="drawer-backdrop" data-close-drawer></div>
  <div class="drawer-panel" role="dialog" aria-modal="true" aria-label="{E(ui('menu'))}">
    <div class="drawer-top"><img src="{u('/assets/img/logo.png')}" alt="" width="80" height="44"><button type="button" class="icon-btn" data-close-drawer aria-label="{E(ui('menuClose'))}">{ICON['close']}</button></div>
    <nav aria-label="{E(ui('mobileNav'))}"><a href="{u(home)}">{E(ui('home'))}</a>{''.join(drawer_links)}<a href="{u(lpath('page', 'club'))}">{E(ui('club'))}</a></nav>
    <p class="drawer-langs">{ICON['globe']} {drawer_langs}</p>
    <div class="drawer-cta">
      <a class="btn btn--primary" href="{u(lpath('shop'))}">{E(ui('orderOnline'))}</a>
      <a class="btn btn--ghost" href="tel:{SITE['phoneIntl']}">{ICON['phone']} <span dir="ltr">{SITE['phone']}</span></a>
    </div>
  </div>
</div>"""


def hours_table(bid):
    b = branch(bid)
    rows = "".join(f"<tr><td>{E(T['days'].get(d, d))}</td><td dir=\"ltr\">{h}</td></tr>" for d, h in b["hours"])
    return f'<table class="hours"><tbody>{rows}</tbody></table>'


def footer():
    sh, sa = branch("shilat"), branch("sarona")
    cats = "".join(f'<li><a href="{u(lpath("cat", k))}">{E(cat(k)[0])}</a></li>' for k in CAT_KEYS[1:8])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <a class="footer-logo" href="{u(lpath('page', 'home'))}"><img src="{u('/assets/img/logo.png')}" alt="Sarfati Premium Smokehouse" width="101" height="56" loading="lazy"></a>
        <p>{E(T['tagline'])}. {E(ui('footerAbout'))}</p>
        <div class="social">
          <a href="{SITE['instagram']}" target="_blank" rel="noopener" aria-label="{E(ui('instagram'))}">{ICON['ig']}</a>
          <a href="{SITE['facebook']}" target="_blank" rel="noopener" aria-label="{E(ui('facebook'))}">{ICON['fb']}</a>
          <a href="https://wa.me/{SITE['whatsapp']}" target="_blank" rel="noopener" aria-label="{E(ui('whatsapp'))}">{ICON['wa']}</a>
        </div>
      </div>
      <div>
        <h3>{E(ui('footerShop'))}</h3>
        <ul>{cats}</ul>
      </div>
      <div>
        <h3>{E(sh['name'])}</h3>
        <p class="mb-0"><a href="{sh['waze']}" target="_blank" rel="noopener">{E(sh['address'])}</a><br><a href="tel:{SITE['phoneIntl']}" dir="ltr">{sh['phone']}</a></p>
        {hours_table('shilat')}
      </div>
      <div>
        <h3>{E(sa['name'])}</h3>
        <p class="mb-0"><a href="{sa['waze']}" target="_blank" rel="noopener">{E(sa['address'])}</a><br><a href="tel:+97235252552" dir="ltr">{sa['phone']}</a></p>
        {hours_table('sarona')}
      </div>
    </div>
    <div class="footer-bottom">
      <span>© <span data-year>{date.today().year}</span> {E(SITE['legalName'] if L == 'he' else 'Sarfati Smokers Ltd.')} {E(ui('rights'))}</span>
      <span><a href="{u(lpath('terms'))}">{E(ui('terms'))}</a> · <a href="{u(lpath('page', 'accessibility'))}">{E(ui('accessibility'))}</a> · <a href="{u(lpath('page', 'club'))}">{E(ui('club'))}</a> · <a href="mailto:{SITE['email']}">{SITE['email']}</a></span>
    </div>
  </div>
</footer>
<a class="wa-float" href="https://wa.me/{SITE['whatsapp']}" target="_blank" rel="noopener" aria-label="{E(ui('waAria'))}">{ICON['wa']}</a>
<div class="toast" id="toast" role="status" aria-live="polite"><span></span><a href="{u(lpath('cart'))}">{E(ui('toCart'))}</a></div>"""


def local_business_ld():
    out = []
    for bid in ("shilat", "sarona"):
        b = branch(bid)
        out.append({
            "@type": "Store", "name": f"{T['siteName']} – {b['name']}", "telephone": b["phone"],
            "address": {"@type": "PostalAddress", "streetAddress": b["street"], "addressLocality": b["city"], "addressCountry": "IL"},
            "openingHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "dayOfWeek": [
                    {"Su": "Sunday", "Mo": "Monday", "Tu": "Tuesday", "We": "Wednesday", "Th": "Thursday", "Fr": "Friday"}[d]
                    for d in days.split()], "opens": o, "closes": c} for days, o, c in b["schema"]],
        })
    return {"@context": "https://schema.org", "@type": "FoodEstablishment", "name": T["siteName"], "alternateName": SITE["nameEn"],
            "url": SITE["url"] + lpath("page", "home"), "logo": SITE["url"] + "/assets/img/logo.png", "image": SITE["url"] + "/assets/img/og.jpg",
            "telephone": SITE["phone"], "email": SITE["email"], "servesCuisine": "Smoked fish, Kosher",
            "sameAs": [SITE["instagram"], SITE["facebook"]], "department": out}


FONTS = {
    "he": "family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@500;700",
    "en": "family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@500;700",
    "fr": "family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@500;700",
    "ru": "family=Noto+Sans:wght@400;600;700;800&family=Noto+Serif:wght@500;700",
    "ar": "family=Noto+Sans+Arabic:wght@400;600;700;800&family=Noto+Naskh+Arabic:wght@500;700",
}


def js_config():
    return {"lang": L, "t": {**T["js"], "nProducts": T["ui"]["nProducts"]}, "catalog": u(f"/assets/data/catalog-{L}.json")}


def page(path, title, description, body, active=None, og_image=None, jsonld=None, noindex=False, full_title=False, alt=None):
    alt = alt or {L: path}
    full = title if full_title else title + T["titleSuffix"]
    og = SITE["url"] + (og_image or "/assets/img/og.jpg")
    canonical = SITE["url"] + path
    ld = "".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>\n' for b in (jsonld or []))
    hreflang = ""
    if len(alt) > 1 and not noindex:
        hreflang = "".join(f'<link rel="alternate" hreflang="{l}" href="{E(SITE["url"] + p)}">\n' for l, p in alt.items())
        hreflang += f'<link rel="alternate" hreflang="x-default" href="{E(SITE["url"] + alt.get("he", path))}">\n'
    doc = f"""<!doctype html>
<html lang="{L}" dir="{T['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">
{hreflang}{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="website">
<meta property="og:locale" content="{T['locale']}">
<meta property="og:site_name" content="{E(T['siteName'])}">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{E(canonical)}">
<meta property="og:image" content="{E(og)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1b2d57">
<link rel="icon" type="image/png" href="{u('/assets/img/favicon.png')}">
<link rel="apple-touch-icon" href="{u('/assets/img/apple-touch-icon.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS[L]}&display=swap">
<link rel="stylesheet" href="{u('/assets/css/style.css')}?v={ASSET_VER}">
<script src="{u('/assets/js/config.js')}?v={ASSET_VER}"></script>
<script>Object.assign(window.SARFATI, {json.dumps(js_config(), ensure_ascii=False)});</script>
<script src="{u('/assets/js/site.js')}?v={ASSET_VER}" defer></script>
{ld}</head>
<body>
{header(active, alt)}
<main id="main">
{body}
</main>
{footer()}
</body>
</html>
"""
    write(path, doc)
    if not noindex:
        SITEMAP.append(path)


def write(path, content):
    target = OUT / path.strip("/") / "index.html" if path.endswith("/") else OUT / path.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def page_hero(title, intro="", crumbs=None):
    bc = ""
    if crumbs:
        parts = [f'<a href="{u(lpath("page", "home"))}">{E(ui("home"))}</a>'] + [f'<a href="{u(p)}">{E(l)}</a>' if p else E(l) for l, p in crumbs]
        bc = f'<nav class="breadcrumbs" aria-label="{E(ui("breadcrumbs"))}">' + '<span aria-hidden="true">/</span>'.join(parts) + "</nav>"
    return f"""<section class="page-hero"><div class="wrap">{bc}<h1>{E(title)}</h1>{f'<p>{intro}</p>' if intro else ''}</div></section>"""


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE["url"] + p} for i, (n, p) in enumerate(items)]}


# ---------------------------------------------------------------- content pages
GALLERY = ["platter-rosettes", "storefront", "salmon-plate", "smoked-trout-platter", "fish-counter", "deli-buffet", "platter-round",
           "packaged-trout", "salmon-tartare", "shop-shelves", "deli-bar", "hot-smoked-fish", "fish-cigars", "wine-shelves",
           "deli-snacks", "fridges", "cat-gifts", "deli-terrace"]
CLIENTS = [("r1", "Delicatessen Yehuda Halevy", 128), ("r2", "Nehemia", 90), ("r3", "Oneg Bayit VaGan", 90), ("r4", "Delicatessen 4 Seasons", 72),
           ("r5", "Terminal 3", 90), ("r6", "Meatliz", 90), ("r7", "Shlosha Katzavim", 128), ("r8", "HaGoren", 128), ("r9", "Maadanina", 90)]
CLIENTS_TITLE = {"he": "הדגים שלנו נמכרים גם ב־", "en": "Our fish is also sold at", "fr": "Nos poissons sont aussi vendus chez",
                 "ru": "Нашу рыбу также продают в", "ar": "تُباع أسماكنا أيضًا في"}


def render_placeholders(text):
    s = SITE["shipping"]

    def products_block(m):
        key, n = m.group(1), int(m.group(2))
        if key == "featured":
            items = [p for i in FEATURED for p in PRODUCTS if p["id"] == i and p["inStock"]]
        else:
            items = [p for p in PRODUCTS if key in p["categories"] and p["inStock"]]
        return '<div class="product-grid">' + "".join(product_card(p) for p in items[:n]) + "</div>"

    def zones():
        return '<div class="zones">' + "".join(
            f'<div class="zone"><strong>{E(T["zones"][z["id"]][0])}</strong><span>{E(T["zones"][z["id"]][1])}</span></div>' for z in s["zones"]) + "</div>"

    def posts_block(m):
        return '<div class="grid grid-3">' + "".join(post_card(p) for p in POSTS[:int(m.group(1))]) + "</div>"

    def cat_cards():
        keys = ["smoked", "platters", "salads", "hot", "frozen", "fresh", "gifts", "drinks"]
        return '<div class="grid grid-4">' + "".join(
            f'<a class="cat-card" href="{u(lpath("cat", k))}">{site_img(CAT_IMG[k], "", w=600, h=600)}<span>{E(cat(k)[0])}</span></a>'
            for k in keys) + "</div>"

    def clients():
        imgs = "".join(f'<img src="{u(f"/assets/img/clients/{f}.png")}" alt="{E(a)}" loading="lazy" width="{w}" height="72">' for f, a, w in CLIENTS)
        return f'<section class="section section--sand section--tight"><div class="wrap center"><span class="eyebrow">{E(CLIENTS_TITLE[L])}</span><div class="logos mt-2">{imgs}</div></div></section>'

    def gallery():
        alts_ = T.get("galleryAlt") or [""] * len(GALLERY)
        figs = "".join(f"<figure>{site_img(g, a)}</figure>" for g, a in zip(GALLERY, alts_))
        return f'<section class="section"><div class="wrap masonry">{figs}</div></section>'

    def link(m):
        key = m.group(1)
        if key.startswith("cat:"):
            return u(lpath("cat", key[4:]))
        if key in ("shop", "cart", "terms", "blog"):
            return u(lpath(key))
        return u(lpath("page", key))

    reps = {
        "{{phone}}": SITE["phone"], "{{phoneIntl}}": SITE["phoneIntl"], "{{whatsapp}}": SITE["whatsapp"],
        "{{whatsappDisplay}}": SITE["whatsappDisplay"], "{{email}}": SITE["email"], "{{wolt}}": SITE["wolt"],
        "{{instagram}}": SITE["instagram"], "{{facebook}}": SITE["facebook"],
        "{{minOrder}}": money(s["minOrder"]), "{{fee}}": money(s["fee"]), "{{freeOver}}": money(s["freeOver"]),
        "{{cutoff}}": T["cutoff"], "{{officeHours}}": T["officeHours"],
    }
    for bid in ("shilat", "sarona"):
        b = branch(bid)
        reps[f"{{{{waze:{bid}}}}}"] = b["waze"]
        reps[f"{{{{maps:{bid}}}}}"] = b["maps"]
        reps[f"{{{{address:{bid}}}}}"] = E(b["address"])
        reps[f"{{{{branch:{bid}}}}}"] = E(b["name"])
    # prefix the page's own root links first, before inserting generated HTML that already has the base
    text = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{BASE}/', text)
    for k, v in reps.items():
        text = text.replace(k, v)
    text = re.sub(r"\{\{link:([\w:]+)\}\}", link, text)
    text = re.sub(r"\{\{icon:(\w+)\}\}", lambda m: ICON[m.group(1)], text)
    text = re.sub(r"\{\{hours:(\w+)\}\}", lambda m: hours_table(m.group(1)), text)
    text = re.sub(r"\{\{products:(\w+):(\d+)\}\}", products_block, text)
    text = re.sub(r"\{\{posts:(\d+)\}\}", posts_block, text)
    text = text.replace("{{zones}}", zones()).replace("{{categories}}", cat_cards())
    text = text.replace("{{clients}}", clients()).replace("{{gallery}}", gallery())
    text = re.sub(r"\{\{img:([\w-]+)\|([^}]*)\}\}", lambda m: site_img(m.group(1), m.group(2)), text)
    return text


def read_page(f):
    raw = f.read_text(encoding="utf-8")
    m = re.match(r"<!--(.*?)-->\s*", raw, re.S)
    meta = dict(re.findall(r"^\s*(\w+):\s*(.+?)\s*$", m.group(1), re.M))
    return meta, raw[m.end():]


def build_content_pages():
    for f in (ROOT / "content/pages/he").glob("*.html"):
        HE_PAGE_PATH[f.stem] = read_page(f)[0]["path"]
    for lang in LANGS:
        set_lang(lang)
        for f in sorted((ROOT / "content/pages" / lang).glob("*.html")):
            pid = f.stem
            meta, raw = read_page(f)
            path = lpath("page", pid)
            body = render_placeholders(raw)
            if meta.get("hero_title"):
                crumbs = [(meta["hero_title"], None)] if pid != "home" else None
                body = page_hero(meta["hero_title"], meta.get("hero_intro", ""), crumbs) + body
            ld = []
            if meta.get("schema") == "business":
                ld.append(local_business_ld())
            if pid != "home":
                ld.append(breadcrumb_ld([(ui("home"), lpath("page", "home")), (meta.get("hero_title", meta["title"]), path)]))
            active = meta.get("active", pid)
            active_path = active if active.startswith("/") else lpath("page", active)
            page(path, meta["title"], meta["description"], body, active=active_path, jsonld=ld,
                 full_title=meta.get("full_title") == "yes", og_image=meta.get("og"), alt=alts("page", pid))


# ---------------------------------------------------------------- shop
def chips(active_key):
    cur = ' aria-current="page"'
    return f'<nav class="chips" aria-label="{E(ui("categories"))}">' + "".join(
        f'<a class="chip" href="{u(lpath("cat", k))}"{cur if k == active_key else ""}>{E(cat(k)[0])}</a>'
        for k in CAT_KEYS) + "</nav>"


def ordering_strip():
    s = SITE["shipping"]
    return f"""<section class="section section--sand section--tight"><div class="wrap grid grid-3">
  <div class="feature"><div class="feature-icon">{ICON['snow']}</div><div><h3>{E(ui('f1t'))}</h3><p>{E(ui('f1d', fee=money(s['fee']), free=money(s['freeOver'])))}</p></div></div>
  <div class="feature"><div class="feature-icon">{ICON['wa']}</div><div><h3>{E(ui('f2t'))}</h3><p>{E(ui('f2d'))}</p></div></div>
  <div class="feature"><div class="feature-icon">{ICON['pin']}</div><div><h3>{E(ui('f3t'))}</h3><p>{E(ui('f3d'))}</p></div></div>
</div></section>"""


def shop_page(key, path, title, intro, items, crumbs, note="", alt=None):
    cards = "".join(product_card(p, i) for i, p in enumerate(sorted_products(items)))
    kosher_opts = "".join(f'<option value="{k}">{E(kosher_name(k))}</option>' for k in KOSHER_KEYS)
    wa = f"https://wa.me/{SITE['whatsapp']}"
    body = page_hero(title, E(intro), crumbs) + f"""
<section class="section section--tight"><div class="wrap shop-layout">
  {chips(key)}
  {note}
  <div class="toolbar">
    <div class="field"><label class="sr-only" for="shop-search">{E(ui('searchLabel'))}</label>
      <input type="search" id="shop-search" placeholder="{E(ui('searchPh'))}" autocomplete="off"></div>
    <div class="actions" style="align-items:center">
      <label class="sr-only" for="shop-kosher">{E(ui('kosherFilter'))}</label>
      <select id="shop-kosher"><option value="">{E(ui('allKosher'))}</option>{kosher_opts}</select>
      <label class="sr-only" for="shop-sort">{E(ui('sort'))}</label>
      <select id="shop-sort"><option value="default">{E(ui('sortDefault'))}</option><option value="price-asc">{E(ui('sortAsc'))}</option>
        <option value="price-desc">{E(ui('sortDesc'))}</option><option value="name">{E(ui('sortName'))}</option></select>
      <span class="result-count" data-result-count>{E(ui('nProducts', n=len(items)))}</span>
    </div>
  </div>
  <div class="product-grid" data-product-grid>{cards}</div>
  <p class="empty-state" data-empty hidden>{ui('empty', wa=wa)}</p>
</div></section>
{ordering_strip()}"""
    ld = [breadcrumb_ld([(ui("home"), lpath("page", "home"))] + [(l, p or path) for l, p in crumbs]),
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": SITE["url"] + lpath("product", p)} for i, p in enumerate(items[:30])]}]
    page(path, title, intro[:155], body, active=lpath("shop"), jsonld=ld, alt=alt)


def build_shop():
    for lang in LANGS:
        set_lang(lang)
        for key in CAT_KEYS:
            label, title, intro = cat(key)
            items = PRODUCTS if key == "all" else [p for p in PRODUCTS if key in p["categories"]]
            crumbs = [(ui("shop"), lpath("shop")), (label, None)] if key != "all" else [(ui("shop"), None)]
            note = f'<p class="note">{E(ui("drinksNote"))}</p>' if key == "drinks" else ""
            shop_page(key, lpath("cat", key), title, intro, items, crumbs, note, alt=alts("cat", key))
        if lang == "he":
            for k in KOSHER_KEYS:
                label = kosher_name(k)
                items = [p for p in PRODUCTS if k in p["kosher"]]
                shop_page(None, KOSHER_HE_PATH[k], ui("kosherPageTitle", k=label), ui("kosherPageIntro", k=label), items,
                          [(ui("shop"), "/shop/"), (ui("kosherPrefix", k=label), None)])


def build_products():
    for lang in LANGS:
        set_lang(lang)
        for p in PRODUCTS:
            build_product(p)


def build_product(p):
    path = lpath("product", p)
    name = pname(p)
    main_cat = next((k for k in CAT_KEYS[1:] if k in p["categories"]), "all")
    imgs = p["images"] or ["assets/img/fish-512.png"]
    wa = f"https://wa.me/{SITE['whatsapp']}"
    thumbs = ""
    if len(imgs) > 1:
        thumbs = '<div class="gallery-thumbs">' + "".join(
            f'<button type="button" data-thumb="{u("/" + im)}" aria-pressed="{"true" if i == 0 else "false"}" aria-label="{E(ui("image", n=i + 1))}">{img_tag(im, "", 74, 74)}</button>'
            for i, im in enumerate(imgs)) + "</div>"
    stock = "1" if p["inStock"] else "0"
    if p.get("variants"):
        opts = "".join(
            f'<option value="{i}" data-label="{E(vlabel(v["label"]))}" data-he-label="{E(v["label"])}" data-price="{v["price"]}" data-stock="{1 if v["inStock"] else 0}"{"" if v["inStock"] else " disabled"}>{E(vlabel(v["label"]))} – {money(v["price"])}{"" if v["inStock"] else " (" + E(ui("outOfStock")) + ")"}</option>'
            for i, v in enumerate(p["variants"]))
        variant_html = f'<div class="field"><label for="variant">{E(ui("weight"))}</label><select id="variant" name="variant">{opts}</select></div>'
        first = next((v for v in p["variants"] if v["inStock"]), p["variants"][0])
        show_price = first["price"]
    else:
        variant_html, show_price = "", p["price"]
    kosher = "".join(
        f'<a class="badge" href="{u(KOSHER_HE_PATH[k] if L == "he" else lpath("page", "kosher"))}">{E(ui("kosherPrefix", k=kosher_name(k)))}</a>'
        for k in p["kosher"] if k in KOSHER_KEYS)
    weighed = ("שקילה" in p["name"] or "לקג" in p["name"].replace(" ", "") or "לאחר שקילה" in p["description"]
               or any("ק״ג" in v["label"] for v in p.get("variants", [])))
    weigh_note = f'<p class="note small">{E(ui("weighNote"))}</p>' if weighed else ""
    related = [r for r in PRODUCTS if r["id"] != p["id"] and r["inStock"] and set(r["categories"]) & set(p["categories"])][:4]
    rel_html = ""
    if related:
        rel_html = f"""<section class="section section--sand"><div class="wrap"><div class="section-head"><h2>{E(ui('related'))}</h2>
<a class="link-arrow" href="{u(lpath('cat', main_cat))}">{E(ui('allOf', cat=cat(main_cat)[0]))}</a></div><div class="product-grid">{''.join(product_card(r) for r in related)}</div></div></section>"""
    desc = pdesc(p)
    oos = "" if p["inStock"] else f'<p class="note">{ui("oosNote", wa=wa)}</p>'
    ask = f"{wa}?text={quote(ui('askAbout', name=name))}"
    body = f"""<nav class="wrap breadcrumbs crumbs-light" aria-label="{E(ui('breadcrumbs'))}"><a href="{u(lpath('page', 'home'))}">{E(ui('home'))}</a><span aria-hidden="true"> / </span><a href="{u(lpath('shop'))}">{E(ui('shop'))}</a><span aria-hidden="true"> / </span><a href="{u(lpath('cat', main_cat))}">{E(cat(main_cat)[0])}</a></nav>
<section class="section" style="padding-top:20px"><div class="wrap product-layout">
  <div>
    <div class="gallery-main">{img_tag(imgs[0], name, 900, 900, lazy=False).replace('<img ', '<img data-gallery-main ')}</div>
    {thumbs}
  </div>
  <div class="product-info">
    <div class="badges" style="margin-bottom:10px">{kosher}</div>
    <h1>{E(name)}</h1>
    <div class="product-price" data-price-display>{money(show_price)}</div>
    {oos}
    <div class="buy-box" data-buy-box data-id="{p['id']}" data-name="{E(name)}" data-he="{E(p['name'])}" data-price="{p['price']}" data-stock="{stock}" data-image="{u('/' + imgs[0])}">
      {variant_html}
      <div class="buy-row">
        <div class="qty"><button type="button" data-qty="1" aria-label="{E(ui('qtyPlus'))}">+</button><input type="number" name="qty" value="1" min="1" max="99" aria-label="{E(ui('qty'))}"><button type="button" data-qty="-1" aria-label="{E(ui('qtyMinus'))}">−</button></div>
        <button type="button" class="btn btn--primary" data-add-product>{E(ui('addToCart'))}</button>
      </div>
      <ul class="trust-list">
        <li>{ICON['check']} {E(ui('trust1', free=money(SITE['shipping']['freeOver'])))}</li>
        <li>{ICON['check']} {E(ui('trust2'))}</li>
        <li>{ICON['check']} {ui('trust3', wa=E(ask))}</li>
      </ul>
    </div>
    {weigh_note}
    <div class="prose">{fix_links(desc) if desc else ''}</div>
  </div>
</div></section>
{rel_html}"""
    summary = (psummary(p) or name)[:150]
    offers = {"@type": "Offer", "priceCurrency": "ILS", "price": f"{show_price:.2f}",
              "availability": "https://schema.org/" + ("InStock" if p["inStock"] else "OutOfStock"), "url": SITE["url"] + path}
    if p.get("variants"):
        offers = {"@type": "AggregateOffer", "priceCurrency": "ILS", "lowPrice": f"{min(v['price'] for v in p['variants']):.2f}",
                  "highPrice": f"{max(v['price'] for v in p['variants']):.2f}", "offerCount": len(p["variants"]),
                  "availability": offers["availability"]}
    ld = [{"@context": "https://schema.org", "@type": "Product", "name": name, "description": summary,
           "image": [SITE["url"] + "/" + im for im in imgs], "brand": {"@type": "Brand", "name": "Sarfati"}, "offers": offers},
          breadcrumb_ld([(ui("home"), lpath("page", "home")), (ui("shop"), lpath("shop")), (cat(main_cat)[0], lpath("cat", main_cat)), (name, path)])]
    page(path, name, f"{name} – {summary}", body, active=lpath("shop"), og_image="/" + imgs[0], jsonld=ld, alt=alts("product", p))


def build_catalogs():
    for lang in LANGS:
        set_lang(lang)
        data = [{"id": p["id"], "name": pname(p), "he": p["name"], "price": p["price"], "inStock": p["inStock"],
                 "url": u(lpath("product", p)), "image": u("/" + p["images"][0]) if p["images"] else "",
                 "variants": [{"label": vlabel(v["label"]), "he": v["label"], "price": v["price"], "inStock": v["inStock"]}
                              for v in p.get("variants", [])]} for p in PRODUCTS]
        (OUT / f"assets/data/catalog-{lang}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- blog (Hebrew)
def fmt_date(d):
    y, m, dd = d.split("-")
    return f"{int(dd)}.{int(m)}.{y}"


def post_card(p):
    return f"""<a class="card post-card" href="{u('/' + p['slug'] + '/')}">{img_tag(p['image'], p['imageAlt'], 1200, 750)}
<div class="card-body"><time datetime="{p['date']}">{fmt_date(p['date'])}</time><h3>{E(p['title'])}</h3><p>{E(p['excerpt'][:140])}…</p></div></a>"""


def build_blog():
    set_lang("he")
    body = page_hero("הבלוג של צרפתי", "מתכונים, רעיונות הגשה וכל מה שכדאי לדעת על דגים מעושנים, כבושים וטריים.", [("בלוג", None)]) + \
        f'<section class="section"><div class="wrap"><div class="grid grid-3">{"".join(post_card(p) for p in POSTS)}</div></div></section>'
    page("/בלוג/", "בלוג – מתכונים וטיפים על דגים מעושנים", "מתכונים, רעיונות הגשה וטיפים על דגים מעושנים, כבושים, טריים וקפואים מבית צרפתי.", body, active="/בלוג/")
    for p in POSTS:
        path = f"/{p['slug']}/"
        others = [o for o in POSTS if o["slug"] != p["slug"]][:3]
        body = page_hero(p["title"], f'<time datetime="{p["date"]}">{fmt_date(p["date"])}</time>', [("בלוג", "/בלוג/"), (p["title"], None)]) + f"""
<article class="section"><div class="narrow">
  <div class="post-hero">{img_tag(p['image'], p['imageAlt'], 1200, 750, lazy=False)}</div>
  <div class="prose">{fix_links(p['body'])}</div>
  <div class="note mt-3">רוצים לטעום? <a href="{u('/shop/')}">לחנות שלנו</a> – משלוח בקירור עד הבית, או איסוף משילת ומשרונה מרקט.</div>
</div></article>
<section class="section section--sand"><div class="wrap"><div class="section-head"><h2>עוד מהבלוג</h2><a class="link-arrow" href="{u('/בלוג/')}">לכל הכתבות</a></div>
<div class="grid grid-3">{''.join(post_card(o) for o in others)}</div></div></section>"""
        ld = [{"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "datePublished": p["date"],
               "image": SITE["url"] + "/" + p["image"], "author": {"@type": "Organization", "name": SITE["name"]},
               "publisher": {"@type": "Organization", "name": SITE["name"], "logo": {"@type": "ImageObject", "url": SITE["url"] + "/assets/img/logo.png"}}},
              breadcrumb_ld([("דף הבית", "/"), ("בלוג", "/בלוג/"), (p["title"], path)])]
        page(path, p["title"], p["excerpt"][:155], body, active="/בלוג/", og_image="/" + p["image"], jsonld=ld)


def fix_links(text):
    return re.sub(r'href="(?!https?:|mailto:|tel:|#)([^"]*)"', lambda m: f'href="{map_old_link(m.group(1))}"', text)


def map_old_link(href):
    mapping = {"shop.html": lpath("shop"), "index.html": lpath("page", "home"), "story.html": lpath("page", "story"),
               "kosher.html": lpath("page", "kosher"), "deli.html": lpath("page", "deli"), "contact.html": lpath("page", "contact"),
               "delivery.html": lpath("page", "delivery")}
    if href in mapping:
        return u(mapping[href])
    m = re.match(r"post\.html\?p=(.+)", href)
    if m:
        return u(f"/{m.group(1)}/")
    return u("/" + href.lstrip("/"))


# ---------------------------------------------------------------- cart / checkout
LOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>'


def pay_buttons():
    if PAYMENTS:
        return f"""<button type="submit" class="btn btn--primary btn--block mt-2" data-submit-order data-pay="card">{LOCK} {E(ui('payCard'))}</button>
        <p class="small muted mt-2 mb-0">{E(ui('paySecure'))}</p>
        <p class="small mt-2 mb-0"><button type="submit" class="linklike" data-pay="wa">{E(ui('orWhatsapp'))}</button></p>"""
    return f"""<button type="submit" class="btn btn--wa btn--block mt-2" data-submit-order data-pay="wa">{ICON['wa']} {E(ui('sendWa'))}</button>
        <p class="small muted mt-2 mb-0">{E(ui('payNote'))} <a href="tel:{SITE['phoneIntl']}" dir="ltr">{SITE['phone']}</a></p>"""


def build_cart():
    s = SITE["shipping"]
    for lang in LANGS:
        set_lang(lang)
        zones = "".join(f'<option value="{z["id"]}">{E(T["zones"][z["id"]][0])} – {E(T["zones"][z["id"]][1])}</option>' for z in s["zones"])
        body = page_hero(ui("cartTitle"), E(ui("cartIntroPay" if PAYMENTS else "cartIntro")), [(ui("cartTitle"), None)]) + f"""
<section class="section" data-cart-page><div class="wrap">
  <div class="note" data-paid hidden><strong>{E(ui('paidTitle'))}</strong><br>{E(ui('paidText'))} <span data-order-ref></span></div>
  <div class="note note--err" data-failed hidden>{E(ui('failedText'))}</div>
  <div data-cart-empty hidden class="empty-state">
    <h2>{E(ui('cartEmpty'))}</h2><p>{E(ui('cartEmptyText'))}</p><a class="btn btn--primary" href="{u(lpath('shop'))}">{E(ui('toShop'))}</a>
  </div>
  <div data-cart-filled class="cart-layout">
    <div>
      <ul class="cart-items" data-cart-items></ul>
      <form id="checkout-form" class="form-card mt-3" novalidate>
        <h2>{E(ui('orderDetails'))}</h2>
        <fieldset style="border:0;padding:0;margin:0 0 18px"><legend class="field" style="font-weight:700;margin-bottom:8px">{E(ui('howReceive'))}</legend>
          <div class="radio-cards">
            <label class="radio-card"><input type="radio" name="method" value="delivery" checked><strong>{E(ui('mDelivery'))}</strong><span>{E(ui('mDeliveryD'))}</span></label>
            <label class="radio-card"><input type="radio" name="method" value="shilat"><strong>{E(ui('mShilat'))}</strong><span>{E(ui('mShilatD'))}</span></label>
            <label class="radio-card"><input type="radio" name="method" value="sarona"><strong>{E(ui('mSarona'))}</strong><span>{E(ui('mSaronaD'))}</span></label>
          </div>
        </fieldset>
        <div class="form-grid two">
          <div class="field"><label for="co-name">{E(ui('fName'))}</label><input id="co-name" name="name" type="text" autocomplete="name" required></div>
          <div class="field"><label for="co-phone">{E(ui('fPhone'))}</label><input id="co-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel" pattern="[0-9+\\-\\s]{{9,15}}" required></div>
          <div class="field full"><label for="co-email">{E(ui('fEmailOpt'))}</label><input id="co-email" name="email" type="email" autocomplete="email"></div>
          <div class="field full" data-delivery-only><label for="co-zone">{E(ui('fZone'))}</label><select id="co-zone" name="zone" data-req required>{zones}</select>
            <span class="hint">{E(ui('fZoneHint', cutoff=T['cutoff']))}</span></div>
          <div class="field" data-delivery-only><label for="co-city">{E(ui('fCity'))}</label><input id="co-city" name="city" type="text" autocomplete="address-level2" data-req required></div>
          <div class="field" data-delivery-only><label for="co-address">{E(ui('fAddress'))}</label><input id="co-address" name="address" type="text" autocomplete="street-address" data-req required></div>
          <div class="field"><label for="co-date">{E(ui('fDate'))}</label><input id="co-date" name="date" type="date"></div>
          <div class="field full"><label for="co-notes">{E(ui('fNotes'))}</label><textarea id="co-notes" name="notes" rows="3"></textarea></div>
          <label class="check full"><input type="checkbox" required> <span>{ui('fAgree', terms=u(lpath('terms')))}</span></label>
        </div>
        {pay_buttons()}
        <div class="form-status" role="status" aria-live="polite"></div>
        <p data-clear-after hidden class="mt-2"><button type="button" class="btn btn--ghost btn--sm" data-clear-cart>{E(ui('clearAfter'))}</button></p>
      </form>
    </div>
    <aside class="form-card cart-summary" aria-label="{E(ui('summaryAria'))}">
      <h2 style="font-size:1.4rem">{E(ui('summary'))}</h2>
      <div class="summary-rows">
        <div><span>{E(ui('subtotal'))}</span><span data-sub>₪0</span></div>
        <div><span>{E(ui('shipping'))}</span><span data-ship>—</span></div>
        <div class="total"><span>{E(ui('total'))}</span><span data-total>₪0</span></div>
      </div>
      <div class="progress" aria-hidden="true"><span data-free-bar style="width:0"></span></div>
      <p class="small" data-free-msg></p>
      <ul class="trust-list small">
        <li>{ICON['check']} {E(ui('sum1', min=money(s['minOrder']), fee=money(s['fee'])))}</li>
        <li>{ICON['check']} {E(ui('sum2', free=money(s['freeOver'])))}</li>
        <li>{ICON['check']} {E(ui('sum3'))}</li>
      </ul>
    </aside>
  </div>
</div></section>"""
        page(lpath("cart"), ui("cartTitle"), ui("cartTitle"), body, active=lpath("shop"), noindex=True, alt=alts("cart"))


# ---------------------------------------------------------------- legal: terms
def build_terms():
    s = SITE["shipping"]
    set_lang("he")
    lines = [l.strip() for l in (ROOT / "content/terms.txt").read_text(encoding="utf-8").splitlines() if l.strip()][2:]
    blocks, cur = [], []
    head_re = re.compile(r"^(\d+\.\s*)?[^.]{2,40}:$")
    new_para = re.compile(r"^(\.?\d+(\.\d+)*\.?\s|\(?\d\)|[•\-])")
    for l in lines:
        l = l.replace("[email protected]", SITE["email"]).replace("לדניאל עורכי דין", "לכותבי התקנון")
        if head_re.match(l):
            if cur:
                blocks.append(("p", " ".join(cur)))
                cur = []
            blocks.append(("h2", l.rstrip(":")))
        elif new_para.match(l) and cur:
            blocks.append(("p", " ".join(cur)))
            cur = [l]
        else:
            cur.append(l)
    if cur:
        blocks.append(("p", " ".join(cur)))
    html_body = "".join(f"<{t}>{E(x)}</{t}>" for t, x in blocks)
    body = page_hero(ui("termsTitle"), "", [(ui("terms"), None)]) + f"""
<section class="section"><div class="narrow legal prose">
<div class="note"><strong>הזמנות דרך האתר:</strong> בחירת המוצרים באתר ושליחת ההזמנה (בוואטסאפ או בטופס) מהווה בקשה להזמנה בלבד.
ההזמנה נחשבת סופית לאחר שנציג צרפתי אישר מולכם טלפונית או בכתב את הזמינות, המשקל הסופי, מועד המסירה והמחיר, והתשלום בוצע.
מוצרים הנמכרים לפי משקל מחויבים לפי השקילה בפועל. מינימום הזמנה למשלוח {money(s['minOrder'])}, דמי משלוח {money(s['fee'])}, משלוח חינם מעל {money(s['freeOver'])}.
ביטול עסקה – בהתאם לחוק הגנת הצרכן; מוצרי מזון פסידים אינם ניתנים להחזרה לאחר המסירה.</div>
{html_body}
</div></section>"""
    page("/תקנון/", ui("termsTitle"), ui("termsDesc"), body, alt=alts("terms"))
    for lang in LANGS[1:]:
        set_lang(lang)
        order = ui("termsOrder", min=money(s["minOrder"]), fee=money(s["fee"]), free=money(s["freeOver"]), email=SITE["email"])
        body = page_hero(ui("termsTitle"), "", [(ui("terms"), None)]) + f"""
<section class="section"><div class="narrow legal prose">
<p class="note">{E(ui('termsHebrew'))} <a href="{u('/תקנון/')}" hreflang="he">{E(ui('termsFull'))}</a></p>
{order}
</div></section>"""
        page(lpath("terms"), ui("termsTitle"), ui("termsDesc"), body, alt=alts("terms"))


# ---------------------------------------------------------------- misc outputs
def build_redirects():
    for old, new in REDIRECTS.items():
        target = u(new)
        write(old, f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>הדף עבר</title>
<meta name="robots" content="noindex"><link rel="canonical" href="{SITE['url']}{new}">
<meta http-equiv="refresh" content="0; url={target}"></head><body><p>הדף עבר. <a href="{target}">המשך</a></p>
<script>location.replace({json.dumps(target)})</script></body></html>""")


def build_404():
    set_lang("he")
    wa = f"https://wa.me/{SITE['whatsapp']}"
    langs = " · ".join(f'<a href="{u(lpath("page", "home", l))}" lang="{l}">{E(I18N[l]["native"])}</a>' for l in LANGS)
    body = page_hero(ui("notFound"), ui("notFoundIntro")) + f"""
<section class="section"><div class="narrow center">
<p>{ui('notFoundText', home=u('/'), shop=u('/shop/'), wa=wa)}</p>
{''.join(f'<a class="chip" style="display:inline-block;margin:4px" href="{u(lpath("cat", k))}">{E(cat(k)[0])}</a>' for k in CAT_KEYS)}
<p class="mt-3" dir="ltr">Page not found · Page introuvable · Страница не найдена · الصفحة غير موجودة</p>
<p>{langs}</p>
</div></section>"""
    page("/404.html", ui("notFound"), ui("notFound"), body, noindex=True)


def build_static():
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    (OUT / "assets/js/config.js").write_text(
        "window.SARFATI = " + json.dumps({
            "base": BASE, "whatsapp": SITE["whatsapp"], "phone": SITE["phone"], "shipping": SITE["shipping"],
            "formEndpoint": SITE.get("formEndpoint", ""), "formAccessKey": SITE.get("formAccessKey", ""),
            "payments": PAYMENTS, "checkoutUrl": u("/api/checkout"),
        }, ensure_ascii=False) + ";\n", encoding="utf-8")
    sh = SITE["shipping"]
    (OUT / "assets/data/shop-rules.json").write_text(
        json.dumps({"minOrder": sh["minOrder"], "fee": sh["fee"], "freeOver": sh["freeOver"]}), encoding="utf-8")
    for extra in ("CNAME",):
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, OUT / extra)
    (OUT / ".nojekyll").touch()
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /cart/\n\nSitemap: {SITE['url']}/sitemap.xml\n", encoding="utf-8")


def build_sitemap():
    urls = "".join(f"<url><loc>{E(SITE['url'] + quote(p))}</loc><lastmod>{TODAY}</lastmod></url>" for p in SITEMAP)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    build_static()
    build_content_pages()
    build_shop()
    build_products()
    build_catalogs()
    build_blog()
    build_cart()
    build_terms()
    build_404()
    build_redirects()
    build_sitemap()
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"Built {n} HTML files in {len(LANGS)} languages into {OUT.relative_to(ROOT)}/ (base path: '{BASE or '/'}')")


if __name__ == "__main__":
    main()
