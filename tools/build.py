#!/usr/bin/env python3
"""Build the static Sarfati website into ./_site

Usage:  python3 tools/build.py            (output in _site/)
        BASE_PATH=/Test-repo python3 tools/build.py   (when served from a sub-folder)

Only the Python standard library is needed.
Edit content in:  content/site.json, content/pages/*.html, assets/data/products.json, assets/data/posts.json
"""
import html
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")
SITE = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
PRODUCTS = json.loads((ROOT / "assets/data/products.json").read_text(encoding="utf-8"))
POSTS = json.loads((ROOT / "assets/data/posts.json").read_text(encoding="utf-8"))
ASSET_VER = str(int(max(p.stat().st_mtime for p in (ROOT / "assets").rglob("*.*") if p.suffix in (".css", ".js"))))
TODAY = date.today().isoformat()
E = html.escape
SITEMAP = []


def u(path):
    """Site-absolute URL with optional base path."""
    return BASE + path


def money(n):
    return f"₪{n:,.0f}" if float(n).is_integer() else f"₪{n:,.2f}"


# ---------------------------------------------------------------- catalogue
CATS = [
    # key, menu label, path, page title, intro, image
    ("all", "כל המוצרים", "/shop/", "חנות דגים מעושנים אונליין",
     "כל המוצרים של צרפתי במקום אחד – סלמון ודגים מעושנים, סלטי דגים, מגשי אירוח, דגים טריים וקפואים. משלוח בקירור עד הבית.", "cat-smoked"),
    ("smoked", "דגים מעושנים וכבושים", "/product-category/דגים-מעושנים/", "דגים מעושנים וכבושים",
     "סלמון, טונה, הליבוט, פורל והרינג – מעושנים אצלנו במפעל בשילת בתהליך בוטיק, על עץ אמיתי ובעבודת יד.", "cat-smoked"),
    ("cold", "עישון קר", "/product-category/דגים-מעושנים/דגים-בעישון-קר/", "דגים בעישון קר",
     "עישון קר בטמפרטורה נמוכה שומר על מרקם רך ומשיי וטעם מעושן עדין. הבחירה הקלאסית לבייגל, לפלטות ולשולחן השבת.", "salmon-plate"),
    ("hot", "עישון חם", "/product-category/דגים-מעושנים/דגים-בעישון-חם/", "דגים בעישון חם",
     "עישון חם מבשל את הדג תוך כדי עישון ומעניק מרקם מתפרק ועסיסי וטעם עמוק. מושלם כמנה עיקרית, בסלט או קר כמנה ראשונה.", "cat-hot-smoked"),
    ("salads", "סלטי דגים", "/product-category/סלטי-דגים-מעושנים/", "סלטי דגים מעושנים",
     "סלטי דגים מעושנים, הרינג ומטיאס כבושים – מוכנים להגשה, בדיוק כמו במעדניות של פעם.", "cat-salads"),
    ("platters", "מגשי אירוח", "/product-category/מגשים-לאירועים/", "מגשי דגים מעושנים לאירועים",
     "מגשי אירוח מעוצבים לשבת, לחג, לבריתות ולפגישות עסקיות. מוכנים להגשה ומגיעים בקירור עד אליכם.", "platter-rosettes"),
    ("frozen", "דגים קפואים", "/product-category/דגים-קפואים/", "דגים קפואים",
     "פילה סלמון, טונה אדומה, הליבוט, הייק ובורגרים – מוקפאים בשיא הטריות כדי שיחכו לכם במקפיא לכל ארוחה.", "cat-frozen"),
    ("fresh", "דגים טריים", "/product-category/דגים-טריים/", "דגים טריים",
     "לברק, דניס, פילטים וסטייקים – מבחר דגים לבישול בבית, נבחרים בקפידה.", "cat-fresh"),
    ("premium", "מעדנים מיוחדים", "/product-category/מוצרים-מיוחדים-פרימיום/", "מוצרי פרימיום מיוחדים",
     "אנשובי מקנטבריה, טונה בשמן זית, ממרח ביצי קוד ומארזי דליקטס – מעדנים שבחרנו במיוחד בשבילכם.", "products-collage"),
    ("gifts", "מארזים ומתנות", "/product-category/מתנות/", "מארזי מתנה",
     "מארזי גורמה ומתנות מפנקות לחגים, לעובדים וללקוחות – סלמון מעושן, יין ומעדנים במארז אחד.", "cat-gifts"),
    ("drinks", "יין ואלכוהול", "/product-category/אלכוהול/", "יינות וקוקטיילים",
     "יינות גלעד וקוקטיילים על בסיס ערק שמתאימים בדיוק לדגים שלנו. מכירת אלכוהול לבני 18 ומעלה בלבד.", "cat-wine"),
]
CAT_BY_KEY = {c[0]: c for c in CATS}
KOSHER = {
    "eda": ("בד״ץ העדה החרדית", "/product-category/כשר-בדץ-העדה-החרדית/"),
    "mehadrin": ("מהדרין חבל מודיעין", "/product-category/כשר-מהדרין-רבנות-חבל-מודיעין-הרהג-אהרן/"),
    "beityosef": ("בד״ץ בית יוסף", "/product-category/בדץ-בית-יוסף/"),
}
FEATURED = [844, 699, 1127, 1120, 760, 1890, 875, 1562]

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
    "/en/": "/",
    "/fr/": "/",
}


def product_url(p):
    return f"/product/{p['slug']}/"


def img_tag(src, alt, w=None, h=None, cls="", lazy=True, sizes=None):
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
        return f'<span class="price-now">החל מ־{money(p["price"])}</span>'
    return f'<span class="price-now">{money(p["price"])}</span>'


def product_card(p, order=0):
    img = p["images"][0] if p["images"] else "assets/img/fish-512.png"
    url = u(product_url(p))
    out = "" if p["inStock"] else '<span class="badge badge--out">אזל מהמלאי</span>'
    if not p["inStock"]:
        action = f'<a class="btn btn--ghost btn--sm" href="{url}">פרטים</a>'
    elif p.get("variants"):
        action = f'<a class="btn btn--ghost btn--sm" href="{url}">בחירת משקל</a>'
    else:
        action = (f'<button type="button" class="btn btn--primary btn--sm" data-add="{p["id"]}" data-name="{E(p["name"])}" '
                  f'data-price="{p["price"]}" data-image="{u("/" + img)}" data-url="{url}">הוספה לסל</button>')
    kosher = " ".join(p["kosher"])
    search = E((p["name"] + " " + p["summary"]).lower())
    badges = "".join(f'<span class="badge">{KOSHER[k][0]}</span>' for k in p["kosher"] if k in KOSHER)
    return f"""<article class="p-card{'' if p['inStock'] else ' is-out'}" data-price="{p['price']}" data-name="{E(p['name'])}" data-order="{order}" data-kosher="{kosher}" data-search="{search}">
  {out}<a class="p-img" href="{url}" tabindex="-1" aria-hidden="true">{img_tag(img, p['name'], 600, 600)}</a>
  <div class="p-body">
    <h3><a href="{url}">{E(p['name'])}</a></h3>
    <div class="badges">{badges}</div>
    <div class="p-price">{price_html(p)}</div>
    <div class="p-actions">{action}</div>
  </div>
</article>"""


def sorted_products(items):
    return sorted(items, key=lambda p: (not p["inStock"], 0))


# ---------------------------------------------------------------- icons
ICON = {
    "cart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    "truck": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h11v10H3zM14 9h4l3 3v4h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/></svg>',
    "snow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 2v20M4 6l16 12M20 6L4 18M9 3l3 3 3-3M9 21l3-3 3 3"/></svg>',
    "flame": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22c4 0 7-2.7 7-7 0-4-3-6-4-9-1 2-2 3-3.5 3.5C11 6 10 4 10 2 6 5 5 9.5 5 15c0 4.3 3 7 7 7z"/></svg>',
    "hand": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 11V5.5a1.5 1.5 0 0 1 3 0V11M10 10V4a1.5 1.5 0 0 1 3 0v6M13 10V5a1.5 1.5 0 0 1 3 0v7M16 11V8a1.5 1.5 0 0 1 3 0v6a8 8 0 0 1-8 8h-.5A6.5 6.5 0 0 1 5 17l-2-4a1.5 1.5 0 0 1 2.6-1.5L7 14"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    "star": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>',
    "wa": '<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true"><path d="M16 3a13 13 0 0 0-11.2 19.6L3 29l6.6-1.7A13 13 0 1 0 16 3zm0 23.7a10.7 10.7 0 0 1-5.5-1.5l-.4-.2-3.9 1 1-3.8-.2-.4A10.7 10.7 0 1 1 16 26.7zm5.9-8c-.3-.2-1.9-1-2.2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7 0a8.8 8.8 0 0 1-4.4-3.8c-.3-.6.3-.5 1-1.7.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6a1.2 1.2 0 0 0-.9.4 3.7 3.7 0 0 0-1.1 2.7 6.5 6.5 0 0 0 1.3 3.4 14.7 14.7 0 0 0 5.7 5c2.1.9 2.9 1 4 .8a3.4 3.4 0 0 0 2.2-1.6 2.8 2.8 0 0 0 .2-1.6c-.1-.2-.3-.3-.6-.4z"/></svg>',
    "ig": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    "fb": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-7.5H16l.4-3h-2.9V8.6c0-.9.3-1.5 1.5-1.5h1.5V4.4a20 20 0 0 0-2.3-.1c-2.3 0-3.8 1.4-3.8 3.9v2.3H8v3h2.4V21z"/></svg>',
}

# ---------------------------------------------------------------- layout
NAV = [
    ("הסיפור שלנו", "/הסיפור-שלנו/", None),
    ("חנות", "/shop/", [(c[1], c[2]) for c in CATS]),
    ("המעדנייה", "/המעדנייה-שלנו/", [("המעדנייה והתפריט", "/המעדנייה-שלנו/"), ("אירועים אצלנו", "/אירועים-אצלנו/"),
                                    ("גלריה", "/גלריה/")]),
    ("משלוחים", "/להיכן-אנו-מספקים/", [("אזורי משלוח", "/להיכן-אנו-מספקים/"), ("משלוחים בוולט", "/צרפתי-משלוחים-בוולט/")]),
    ("לעסקים", "/עסקים/", None),
    ("כשרות", "/כשרות/", None),
    ("בלוג", "/בלוג/", None),
    ("צור קשר", "/יצירת-קשר/", None),
]


def header(active):
    items = []
    for label, path, sub in NAV:
        cur = ' aria-current="page"' if active == path else ""
        if sub:
            subs = "".join(f'<li><a href="{u(p)}">{E(l)}</a></li>' for l, p in sub)
            items.append(f'<li><button type="button" class="nav-parent" aria-haspopup="true">{E(label)}</button><ul class="sub">{subs}</ul></li>')
        else:
            items.append(f'<li><a href="{u(path)}"{cur}>{E(label)}</a></li>')
    drawer_links = []
    for label, path, sub in NAV:
        drawer_links.append(f'<a href="{u(path)}">{E(label)}</a>')
        if sub and path == "/shop/":
            drawer_links.append('<div class="sub-links">' + "".join(f'<a href="{u(p)}">{E(l)}</a>' for l, p in sub[1:]) + "</div>")
        elif sub:
            drawer_links.append('<div class="sub-links">' + "".join(f'<a href="{u(p)}">{E(l)}</a>' for l, p in sub if p != path) + "</div>")
    s = SITE["shipping"]
    return f"""<a class="skip-link" href="#main">דלג לתוכן</a>
<div class="topbar">משלוחים בקירור עד הבית · משלוח חינם בהזמנה מעל {money(s['freeOver'])} · <a href="{u('/להיכן-אנו-מספקים/')}">ימי חלוקה</a></div>
<header class="site-header">
  <div class="wrap header-inner">
    <button type="button" class="icon-btn menu-toggle" aria-label="פתיחת תפריט" aria-expanded="false" aria-controls="drawer">{ICON['menu']}</button>
    <a class="brand" href="{u('/')}" aria-label="צרפתי – לדף הבית"><img src="{u('/assets/img/logo.png')}" alt="Sarfati Premium Smokehouse" width="90" height="50"></a>
    <nav class="nav" aria-label="ניווט ראשי"><ul>{''.join(items)}</ul></nav>
    <div class="header-actions">
      <a class="header-phone" href="tel:{SITE['phoneIntl']}">{SITE['phone']}</a>
      <a class="icon-btn" href="{u('/cart/')}" aria-label="סל הקניות">{ICON['cart']}<span class="cart-count" data-count="0" aria-live="polite">0</span></a>
    </div>
  </div>
</header>
<div class="drawer" id="drawer" aria-hidden="true">
  <div class="drawer-backdrop" data-close-drawer></div>
  <div class="drawer-panel" role="dialog" aria-modal="true" aria-label="תפריט">
    <div class="drawer-top"><img src="{u('/assets/img/logo.png')}" alt="" width="80" height="44"><button type="button" class="icon-btn" data-close-drawer aria-label="סגירת תפריט">{ICON['close']}</button></div>
    <nav aria-label="ניווט נייד"><a href="{u('/')}">דף הבית</a>{''.join(drawer_links)}<a href="{u('/מועדון-לקוחות/')}">מועדון לקוחות</a></nav>
    <div class="drawer-cta">
      <a class="btn btn--primary" href="{u('/shop/')}">להזמנה אונליין</a>
      <a class="btn btn--ghost" href="tel:{SITE['phoneIntl']}">{ICON['phone']} {SITE['phone']}</a>
    </div>
  </div>
</div>"""


def hours_table(branch_id):
    b = next(b for b in SITE["branches"] if b["id"] == branch_id)
    rows = "".join(f"<tr><td>{d}</td><td>{h}</td></tr>" for d, h in b["hours"])
    return f'<table class="hours"><tbody>{rows}</tbody></table>'


def footer():
    sh, sa = SITE["branches"]
    cats = "".join(f'<li><a href="{u(c[2])}">{E(c[1])}</a></li>' for c in CATS[1:8])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <a class="footer-logo" href="{u('/')}"><img src="{u('/assets/img/logo.png')}" alt="Sarfati Premium Smokehouse" width="101" height="56" loading="lazy"></a>
        <p>{E(SITE['tagline'])}. מעושנים במפעל שלנו בשילת מאז 2015 – מהמשפחה שלנו לשולחן שלכם.</p>
        <div class="social">
          <a href="{SITE['instagram']}" target="_blank" rel="noopener" aria-label="אינסטגרם">{ICON['ig']}</a>
          <a href="{SITE['facebook']}" target="_blank" rel="noopener" aria-label="פייסבוק">{ICON['fb']}</a>
          <a href="https://wa.me/{SITE['whatsapp']}" target="_blank" rel="noopener" aria-label="וואטסאפ">{ICON['wa']}</a>
        </div>
      </div>
      <div>
        <h3>החנות</h3>
        <ul>{cats}</ul>
      </div>
      <div>
        <h3>{E(sh['name'])}</h3>
        <p class="mb-0"><a href="{sh['waze']}" target="_blank" rel="noopener">{E(sh['address'])}</a><br><a href="tel:{SITE['phoneIntl']}">{sh['phone']}</a></p>
        {hours_table('shilat')}
      </div>
      <div>
        <h3>{E(sa['name'])}</h3>
        <p class="mb-0"><a href="{sa['waze']}" target="_blank" rel="noopener">{E(sa['address'])}</a><br><a href="tel:+97235252552">{sa['phone']}</a></p>
        {hours_table('sarona')}
      </div>
    </div>
    <div class="footer-bottom">
      <span>© <span data-year>{date.today().year}</span> {E(SITE['legalName'])}. כל הזכויות שמורות.</span>
      <span><a href="{u('/תקנון/')}">תקנון ומדיניות פרטיות</a> · <a href="{u('/הצהרת-נגישות/')}">הצהרת נגישות</a> · <a href="{u('/מועדון-לקוחות/')}">מועדון לקוחות</a> · <a href="mailto:{SITE['email']}">{SITE['email']}</a></span>
    </div>
  </div>
</footer>
<a class="wa-float" href="https://wa.me/{SITE['whatsapp']}" target="_blank" rel="noopener" aria-label="שליחת הודעת וואטסאפ">{ICON['wa']}</a>
<div class="toast" id="toast" role="status" aria-live="polite"><span></span><a href="{u('/cart/')}">לסל ←</a></div>"""


def local_business_ld():
    out = []
    for b in SITE["branches"]:
        out.append({
            "@type": "Store", "name": f"{SITE['name']} – {b['name']}", "telephone": b["phone"],
            "address": {"@type": "PostalAddress", "streetAddress": b["street"], "addressLocality": b["city"], "addressCountry": "IL"},
            "openingHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "dayOfWeek": [
                    {"Su": "Sunday", "Mo": "Monday", "Tu": "Tuesday", "We": "Wednesday", "Th": "Thursday", "Fr": "Friday"}[d]
                    for d in days.split()], "opens": o, "closes": c} for days, o, c in b["schema"]],
        })
    return {"@context": "https://schema.org", "@type": "FoodEstablishment", "name": SITE["name"], "alternateName": SITE["nameEn"],
            "url": SITE["url"], "logo": SITE["url"] + "/assets/img/logo.png", "image": SITE["url"] + "/assets/img/og.jpg",
            "telephone": SITE["phone"], "email": SITE["email"], "servesCuisine": "Smoked fish, Kosher",
            "sameAs": [SITE["instagram"], SITE["facebook"]], "department": out}


def page(path, title, description, body, active=None, og_image=None, jsonld=None, noindex=False, full_title=False):
    full = title if full_title else f"{title} | צרפתי דגים מעושנים"
    og = SITE["url"] + (og_image or "/assets/img/og.jpg")
    canonical = SITE["url"] + path
    ld = ""
    for block in (jsonld or []):
        ld += f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>\n'
    doc = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="website">
<meta property="og:locale" content="he_IL">
<meta property="og:site_name" content="{E(SITE['name'])}">
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@500;700&display=swap">
<link rel="stylesheet" href="{u('/assets/css/style.css')}?v={ASSET_VER}">
<script src="{u('/assets/js/config.js')}?v={ASSET_VER}"></script>
<script src="{u('/assets/js/site.js')}?v={ASSET_VER}" defer></script>
{ld}</head>
<body>
{header(active)}
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
        parts = [f'<a href="{u("/")}">דף הבית</a>'] + [f'<a href="{u(p)}">{E(l)}</a>' if p else E(l) for l, p in crumbs]
        bc = '<nav class="breadcrumbs" aria-label="פירורי לחם">' + '<span aria-hidden="true">/</span>'.join(parts) + "</nav>"
    return f"""<section class="page-hero"><div class="wrap">{bc}<h1>{E(title)}</h1>{f'<p>{intro}</p>' if intro else ''}</div></section>"""


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE["url"] + p} for i, (n, p) in enumerate(items)]}


# ---------------------------------------------------------------- content pages (content/pages/*.html)
def render_placeholders(text):
    s = SITE["shipping"]

    def products_block(m):
        key, n = m.group(1), int(m.group(2))
        if key == "featured":
            items = [p for i in FEATURED for p in PRODUCTS if p["id"] == i and p["inStock"]]
        else:
            items = [p for p in PRODUCTS if key in p["categories"] and p["inStock"]]
        return '<div class="product-grid">' + "".join(product_card(p) for p in items[:n]) + "</div>"

    def zones(_):
        return '<div class="zones">' + "".join(
            f'<div class="zone"><strong>{E(z["day"])}</strong><span>{E(z["areas"])}</span></div>' for z in s["zones"]) + "</div>"

    def posts_block(m):
        n = int(m.group(1))
        return '<div class="grid grid-3">' + "".join(post_card(p) for p in POSTS[:n]) + "</div>"

    def cat_cards(_):
        keys = ["smoked", "platters", "salads", "hot", "frozen", "fresh", "gifts", "drinks"]
        return '<div class="grid grid-4">' + "".join(
            f'<a class="cat-card" href="{u(CAT_BY_KEY[k][2])}">{site_img(CAT_BY_KEY[k][5], "", w=600, h=600)}<span>{E(CAT_BY_KEY[k][1])}</span></a>'
            for k in keys) + "</div>"

    reps = {
        "{{phone}}": SITE["phone"], "{{phoneIntl}}": SITE["phoneIntl"], "{{whatsapp}}": SITE["whatsapp"],
        "{{whatsappDisplay}}": SITE["whatsappDisplay"], "{{email}}": SITE["email"], "{{wolt}}": SITE["wolt"],
        "{{instagram}}": SITE["instagram"], "{{facebook}}": SITE["facebook"],
        "{{minOrder}}": money(s["minOrder"]), "{{fee}}": money(s["fee"]), "{{freeOver}}": money(s["freeOver"]),
        "{{cutoff}}": s["cutoff"], "{{officeHours}}": SITE["officeHours"],
        "{{hours:shilat}}": hours_table("shilat"), "{{hours:sarona}}": hours_table("sarona"),
    }
    for b in SITE["branches"]:
        reps[f"{{{{waze:{b['id']}}}}}"] = b["waze"]
        reps[f"{{{{maps:{b['id']}}}}}"] = b["maps"]
        reps[f"{{{{address:{b['id']}}}}}"] = b["address"]
    # prefix the page's own root links first, before inserting generated HTML that already has the base
    text = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{BASE}/', text)
    for k, v in reps.items():
        text = text.replace(k, v)
    text = re.sub(r"\{\{products:(\w+):(\d+)\}\}", products_block, text)
    text = re.sub(r"\{\{posts:(\d+)\}\}", posts_block, text)
    text = text.replace("{{zones}}", zones(None)).replace("{{categories}}", cat_cards(None))
    text = re.sub(r"\{\{img:([\w-]+)\|([^}]*)\}\}", lambda m: site_img(m.group(1), m.group(2)), text)
    return text


def build_content_pages():
    for f in sorted((ROOT / "content/pages").glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"<!--(.*?)-->\s*", raw, re.S)
        meta = dict(re.findall(r"^\s*(\w+):\s*(.+?)\s*$", m.group(1), re.M))
        body = render_placeholders(raw[m.end():])
        if meta.get("hero_title"):
            crumbs = [(meta["hero_title"], None)] if meta["path"] != "/" else None
            body = page_hero(meta["hero_title"], meta.get("hero_intro", ""), crumbs) + body
        ld = []
        if meta.get("schema") == "business":
            ld.append(local_business_ld())
        if meta["path"] != "/":
            ld.append(breadcrumb_ld([("דף הבית", "/"), (meta.get("hero_title", meta["title"]), meta["path"])]))
        page(meta["path"], meta["title"], meta["description"], body, active=meta.get("active", meta["path"]),
             jsonld=ld, full_title=meta.get("full_title") == "yes", og_image=meta.get("og"))


# ---------------------------------------------------------------- shop
def chips(active_key):
    out = []
    for key, label, path, *_ in CATS:
        cur = ' aria-current="page"' if key == active_key else ""
        out.append(f'<a class="chip" href="{u(path)}"{cur}>{E(label)}</a>')
    return '<nav class="chips" aria-label="קטגוריות">' + "".join(out) + "</nav>"


def shop_page(key, label, path, title, intro, items, crumbs, note=""):
    cards = "".join(product_card(p, i) for i, p in enumerate(sorted_products(items)))
    kosher_opts = "".join(f'<option value="{k}">{E(v[0])}</option>' for k, v in KOSHER.items())
    body = page_hero(title, E(intro), crumbs) + f"""
<section class="section section--tight"><div class="wrap shop-layout">
  {chips(key)}
  {note}
  <div class="toolbar">
    <div class="field"><label class="sr-only" for="shop-search">חיפוש מוצר</label>
      <input type="search" id="shop-search" placeholder="חיפוש: סלמון, הרינג, מגש…" autocomplete="off"></div>
    <div class="actions" style="align-items:center">
      <label class="sr-only" for="shop-kosher">סינון לפי כשרות</label>
      <select id="shop-kosher"><option value="">כל הכשרויות</option>{kosher_opts}</select>
      <label class="sr-only" for="shop-sort">מיון</label>
      <select id="shop-sort"><option value="default">מומלצים</option><option value="price-asc">מחיר: מהנמוך לגבוה</option>
        <option value="price-desc">מחיר: מהגבוה לנמוך</option><option value="name">לפי שם</option></select>
      <span class="result-count" data-result-count>{len(items)} מוצרים</span>
    </div>
  </div>
  <div class="product-grid" data-product-grid>{cards}</div>
  <p class="empty-state" data-empty hidden>לא נמצאו מוצרים. נסו מילת חיפוש אחרת או <a href="https://wa.me/{SITE['whatsapp']}">שאלו אותנו בוואטסאפ</a>.</p>
</div></section>
{ordering_strip()}"""
    ld = [breadcrumb_ld([("דף הבית", "/")] + [(l, p or path) for l, p in crumbs]),
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": SITE["url"] + product_url(p)} for i, p in enumerate(items[:30])]}]
    page(path, title, intro[:155], body, active="/shop/", jsonld=ld)


def ordering_strip():
    s = SITE["shipping"]
    return f"""<section class="section section--sand section--tight"><div class="wrap grid grid-3">
  <div class="feature"><div class="feature-icon">{ICON['snow']}</div><div><h3>משלוח בקירור</h3><p>עד הבית בימי החלוקה הקבועים. משלוח {money(s['fee'])}, חינם מעל {money(s['freeOver'])}.</p></div></div>
  <div class="feature"><div class="feature-icon">{ICON['wa']}</div><div><h3>מזמינים בקלות</h3><p>בוחרים מוצרים, שולחים את ההזמנה בוואטסאפ ונציג חוזר לאישור ותשלום.</p></div></div>
  <div class="feature"><div class="feature-icon">{ICON['pin']}</div><div><h3>או איסוף עצמי</h3><p>מחנות המפעל בשילת או מהסניף בשרונה מרקט בתל אביב.</p></div></div>
</div></section>"""


def build_shop():
    for key, label, path, title, intro, _img in CATS:
        items = PRODUCTS if key == "all" else [p for p in PRODUCTS if key in p["categories"]]
        crumbs = [("חנות", "/shop/"), (label, None)] if key != "all" else [("חנות", None)]
        note = ""
        if key == "drinks":
            note = '<p class="note">מכירת משקאות אלכוהוליים לבני 18 ומעלה בלבד. בעת המסירה ייתכן שתתבקשו להציג תעודה מזהה.</p>'
        shop_page(key, label, path, title, intro, items, crumbs, note)
    for k, (label, path) in KOSHER.items():
        items = [p for p in PRODUCTS if k in p["kosher"]]
        shop_page(None, label, path, f"מוצרים בכשרות {label}",
                  f"כל המוצרים שלנו בכשרות {label}. לפרטים נוספים על הכשרות ראו את עמוד הכשרות.", items,
                  [("חנות", "/shop/"), (f"כשרות {label}", None)])


def build_products():
    for p in PRODUCTS:
        path = product_url(p)
        main_cat = next((c for c in CATS[1:] if c[0] in p["categories"]), CATS[0])
        imgs = p["images"] or ["assets/img/fish-512.png"]
        thumbs = ""
        if len(imgs) > 1:
            thumbs = '<div class="gallery-thumbs">' + "".join(
                f'<button type="button" data-thumb="{u("/" + im)}" aria-pressed="{"true" if i == 0 else "false"}" aria-label="תמונה {i + 1}">{img_tag(im, "", 74, 74)}</button>'
                for i, im in enumerate(imgs)) + "</div>"
        stock = "1" if p["inStock"] else "0"
        if p.get("variants"):
            opts = "".join(
                f'<option value="{E(v["label"])}" data-price="{v["price"]}" data-stock="{1 if v["inStock"] else 0}"{"" if v["inStock"] else " disabled"}>{E(v["label"])} – {money(v["price"])}{"" if v["inStock"] else " (אזל)"}</option>'
                for v in p["variants"])
            variant_html = f'<div class="field"><label for="variant">משקל</label><select id="variant" name="variant">{opts}</select></div>'
            first = next((v for v in p["variants"] if v["inStock"]), p["variants"][0])
            show_price = first["price"]
        else:
            variant_html, show_price = "", p["price"]
        kosher = "".join(f'<a class="badge" href="{u(KOSHER[k][1])}">כשרות {KOSHER[k][0]}</a>' for k in p["kosher"] if k in KOSHER)
        weighed = ("שקילה" in p["name"] or "לקג" in p["name"].replace(" ", "") or "לאחר שקילה" in p["description"]
                   or any("ק״ג" in v["label"] for v in p.get("variants", [])))
        weigh_note = '<p class="note small">המוצר נשקל בעת ההכנה. המחיר הסופי נקבע לפי המשקל בפועל ויאושר מולכם לפני התשלום.</p>' if weighed else ""
        related = [r for r in PRODUCTS if r["id"] != p["id"] and r["inStock"] and set(r["categories"]) & set(p["categories"])][:4]
        rel_html = ""
        if related:
            rel_html = f"""<section class="section section--sand"><div class="wrap"><div class="section-head"><h2>אולי תאהבו גם</h2>
<a class="link-arrow" href="{u(main_cat[2])}">ל{E(main_cat[1])}</a></div><div class="product-grid">{''.join(product_card(r) for r in related)}</div></div></section>"""
        body = f"""<nav class="wrap breadcrumbs" style="color:var(--muted);padding-top:18px" aria-label="פירורי לחם"><a style="color:var(--navy)" href="{u('/')}">דף הבית</a><span aria-hidden="true"> / </span><a style="color:var(--navy)" href="{u('/shop/')}">חנות</a><span aria-hidden="true"> / </span><a style="color:var(--navy)" href="{u(main_cat[2])}">{E(main_cat[1])}</a></nav>
<section class="section" style="padding-top:20px"><div class="wrap product-layout">
  <div>
    <div class="gallery-main">{img_tag(imgs[0], p['name'], 900, 900, lazy=False).replace('<img ', '<img data-gallery-main ')}</div>
    {thumbs}
  </div>
  <div class="product-info">
    <div class="badges" style="margin-bottom:10px">{kosher}</div>
    <h1>{E(p['name'])}</h1>
    <div class="product-price" data-price-display>{money(show_price)}</div>
    {'' if p['inStock'] else '<p class="note">המוצר אזל זמנית מהמלאי. רוצים שנעדכן כשיחזור? <a href="https://wa.me/' + SITE['whatsapp'] + '">כתבו לנו</a>.</p>'}
    <div class="buy-box" data-buy-box data-id="{p['id']}" data-name="{E(p['name'])}" data-price="{p['price']}" data-stock="{stock}" data-image="{u('/' + imgs[0])}">
      {variant_html}
      <div class="buy-row">
        <div class="qty"><button type="button" data-qty="1" aria-label="הוספת כמות">+</button><input type="number" name="qty" value="1" min="1" max="99" aria-label="כמות"><button type="button" data-qty="-1" aria-label="הפחתת כמות">−</button></div>
        <button type="button" class="btn btn--primary" data-add-product>הוספה לסל</button>
      </div>
      <ul class="trust-list">
        <li>{ICON['check']} משלוח בקירור · חינם מעל {money(SITE['shipping']['freeOver'])}</li>
        <li>{ICON['check']} איסוף עצמי משילת או משרונה מרקט</li>
        <li>{ICON['check']} שאלה על המוצר? <a href="https://wa.me/{SITE['whatsapp']}?text={E('שאלה על ' + p['name'])}">כתבו לנו בוואטסאפ</a></li>
      </ul>
    </div>
    {weigh_note}
    <div class="prose">{fix_links(p['description']) or '<p>' + E(p['summary']) + '</p>'}</div>
  </div>
</div></section>
{rel_html}"""
        desc = (p["summary"] or p["name"])[:150]
        offers = {"@type": "Offer", "priceCurrency": "ILS", "price": f"{show_price:.2f}",
                  "availability": "https://schema.org/" + ("InStock" if p["inStock"] else "OutOfStock"), "url": SITE["url"] + path}
        if p.get("variants"):
            offers = {"@type": "AggregateOffer", "priceCurrency": "ILS", "lowPrice": f"{min(v['price'] for v in p['variants']):.2f}",
                      "highPrice": f"{max(v['price'] for v in p['variants']):.2f}", "offerCount": len(p["variants"]),
                      "availability": offers["availability"]}
        ld = [{"@context": "https://schema.org", "@type": "Product", "name": p["name"], "description": desc,
               "image": [SITE["url"] + "/" + im for im in imgs], "brand": {"@type": "Brand", "name": "Sarfati"}, "offers": offers},
              breadcrumb_ld([("דף הבית", "/"), ("חנות", "/shop/"), (main_cat[1], main_cat[2]), (p["name"], path)])]
        page(path, p["name"], f"{p['name']} – {desc}", body, active="/shop/", og_image="/" + imgs[0], jsonld=ld)


# ---------------------------------------------------------------- blog
def fmt_date(d):
    y, m, dd = d.split("-")
    return f"{int(dd)}.{int(m)}.{y}"


def post_card(p):
    return f"""<a class="card post-card" href="{u('/' + p['slug'] + '/')}">{img_tag(p['image'], p['imageAlt'], 1200, 750)}
<div class="card-body"><time datetime="{p['date']}">{fmt_date(p['date'])}</time><h3>{E(p['title'])}</h3><p>{E(p['excerpt'][:140])}…</p></div></a>"""


def build_blog():
    body = page_hero("הבלוג של צרפתי", "מתכונים, רעיונות הגשה וכל מה שכדאי לדעת על דגים מעושנים, כבושים וטריים.", [("בלוג", None)]) + \
        f'<section class="section"><div class="wrap"><div class="grid grid-3">{"".join(post_card(p) for p in POSTS)}</div></div></section>'
    page("/בלוג/", "בלוג – מתכונים וטיפים על דגים מעושנים", "מתכונים, רעיונות הגשה וטיפים על דגים מעושנים, כבושים, טריים וקפואים מבית צרפתי.", body, active="/בלוג/")
    for p in POSTS:
        path = f"/{p['slug']}/"
        content = fix_links(p["body"])
        others = [o for o in POSTS if o["slug"] != p["slug"]][:3]
        body = page_hero(p["title"], f'<time datetime="{p["date"]}">{fmt_date(p["date"])}</time>', [("בלוג", "/בלוג/"), (p["title"], None)]) + f"""
<article class="section"><div class="narrow">
  <div class="post-hero">{img_tag(p['image'], p['imageAlt'], 1200, 750, lazy=False)}</div>
  <div class="prose">{content}</div>
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
    mapping = {"shop.html": "/shop/", "index.html": "/", "story.html": "/הסיפור-שלנו/", "kosher.html": "/כשרות/",
               "deli.html": "/המעדנייה-שלנו/", "contact.html": "/יצירת-קשר/", "delivery.html": "/להיכן-אנו-מספקים/"}
    if href in mapping:
        return u(mapping[href])
    m = re.match(r"post\.html\?p=(.+)", href)
    if m:
        return u(f"/{m.group(1)}/")
    return u("/" + href.lstrip("/"))


# ---------------------------------------------------------------- cart / checkout
def build_cart():
    s = SITE["shipping"]
    zones = "".join(f'<option value="{z["id"]}">{E(z["day"])} – {E(z["areas"])}</option>' for z in s["zones"])
    body = page_hero("סל הקניות", "בודקים את ההזמנה, ממלאים פרטים ושולחים לנו – נחזור אליכם לאישור ולתשלום.", [("סל הקניות", None)]) + f"""
<section class="section" data-cart-page><div class="wrap">
  <div data-cart-empty hidden class="empty-state">
    <h2>הסל שלכם ריק</h2><p>זה הזמן לבחור משהו טעים.</p><a class="btn btn--primary" href="{u('/shop/')}">לחנות</a>
  </div>
  <div data-cart-filled class="cart-layout">
    <div>
      <ul class="cart-items" data-cart-items></ul>
      <form id="checkout-form" class="form-card mt-3" novalidate>
        <h2>פרטים להזמנה</h2>
        <fieldset style="border:0;padding:0;margin:0 0 18px"><legend class="field" style="font-weight:700;margin-bottom:8px">איך תרצו לקבל את ההזמנה?</legend>
          <div class="radio-cards">
            <label class="radio-card"><input type="radio" name="method" value="delivery" checked><strong>משלוח עד הבית</strong><span>בקירור, בימי החלוקה</span></label>
            <label class="radio-card"><input type="radio" name="method" value="shilat"><strong>איסוף משילת</strong><span>חנות המפעל, גלבוע 2</span></label>
            <label class="radio-card"><input type="radio" name="method" value="sarona"><strong>איסוף משרונה מרקט</strong><span>תל אביב</span></label>
          </div>
        </fieldset>
        <div class="form-grid two">
          <div class="field"><label for="co-name">שם מלא *</label><input id="co-name" name="name" type="text" autocomplete="name" required></div>
          <div class="field"><label for="co-phone">טלפון *</label><input id="co-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel" pattern="[0-9+\\-\\s]{{9,15}}" required></div>
          <div class="field full"><label for="co-email">אימייל (לא חובה)</label><input id="co-email" name="email" type="email" autocomplete="email"></div>
          <div class="field full" data-delivery-only><label for="co-zone">אזור משלוח *</label><select id="co-zone" name="zone" data-req required>{zones}</select>
            <span class="hint">ההזמנה יוצאת ביום החלוקה של האזור שלכם. יש להזמין {E(s['cutoff'])}.</span></div>
          <div class="field" data-delivery-only><label for="co-city">עיר / יישוב *</label><input id="co-city" name="city" type="text" autocomplete="address-level2" data-req required></div>
          <div class="field" data-delivery-only><label for="co-address">רחוב, מספר, דירה *</label><input id="co-address" name="address" type="text" autocomplete="street-address" data-req required></div>
          <div class="field"><label for="co-date">תאריך מבוקש</label><input id="co-date" name="date" type="date"></div>
          <div class="field full"><label for="co-notes">הערות (קוד כניסה, בקשות מיוחדות, עם/בלי עור…)</label><textarea id="co-notes" name="notes" rows="3"></textarea></div>
          <label class="check full"><input type="checkbox" required> <span>קראתי ואני מסכים/ה ל<a href="{u('/תקנון/')}" target="_blank">תקנון האתר</a> *</span></label>
        </div>
        <button type="submit" class="btn btn--wa btn--block mt-2" data-submit-order>{ICON['wa']} שליחת ההזמנה בוואטסאפ</button>
        <p class="small muted mt-2 mb-0">התשלום מתבצע לאחר שנציג מאשר מולכם את ההזמנה, הזמינות והמשקל הסופי. מעדיפים בטלפון? <a href="tel:{SITE['phoneIntl']}">{SITE['phone']}</a></p>
        <div class="form-status" role="status" aria-live="polite"></div>
        <p data-clear-after hidden class="mt-2"><button type="button" class="btn btn--ghost btn--sm" data-clear-cart>ההזמנה נשלחה – לרוקן את הסל</button></p>
      </form>
    </div>
    <aside class="form-card cart-summary" aria-label="סיכום הזמנה">
      <h2 style="font-size:1.4rem">סיכום</h2>
      <div class="summary-rows">
        <div><span>סכום ביניים</span><span data-sub>₪0</span></div>
        <div><span>משלוח</span><span data-ship>—</span></div>
        <div class="total"><span>סה״כ משוער</span><span data-total>₪0</span></div>
      </div>
      <div class="progress" aria-hidden="true"><span data-free-bar style="width:0"></span></div>
      <p class="small" data-free-msg></p>
      <ul class="trust-list small">
        <li>{ICON['check']} מינימום הזמנה למשלוח {money(s['minOrder'])}, דמי משלוח {money(s['fee'])}</li>
        <li>{ICON['check']} משלוח חינם מעל {money(s['freeOver'])}</li>
        <li>{ICON['check']} מוצרים במשקל מחויבים לפי שקילה בפועל</li>
      </ul>
    </aside>
  </div>
</div></section>"""
    page("/cart/", "סל הקניות", "סל הקניות והשלמת הזמנה – צרפתי דגים מעושנים", body, active="/shop/", noindex=True)


# ---------------------------------------------------------------- legal: terms
def build_terms():
    lines = [l.strip() for l in (ROOT / "content/terms.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = lines[2:]  # drop duplicated page title lines
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
    s = SITE["shipping"]
    body = page_hero("תקנון, תנאי שימוש ומדיניות פרטיות", "", [("תקנון", None)]) + f"""
<section class="section"><div class="narrow legal prose">
<div class="note"><strong>הזמנות דרך האתר:</strong> בחירת המוצרים באתר ושליחת ההזמנה (בוואטסאפ או בטופס) מהווה בקשה להזמנה בלבד.
ההזמנה נחשבת סופית לאחר שנציג צרפתי אישר מולכם טלפונית או בכתב את הזמינות, המשקל הסופי, מועד המסירה והמחיר, והתשלום בוצע.
מוצרים הנמכרים לפי משקל מחויבים לפי השקילה בפועל. מינימום הזמנה למשלוח {money(s['minOrder'])}, דמי משלוח {money(s['fee'])}, משלוח חינם מעל {money(s['freeOver'])}.
ביטול עסקה – בהתאם לחוק הגנת הצרכן; מוצרי מזון פסידים אינם ניתנים להחזרה לאחר המסירה.</div>
{html_body}
</div></section>"""
    page("/תקנון/", "תקנון ומדיניות פרטיות", "תקנון האתר, תנאי שימוש, תנאי הזמנה ומשלוח ומדיניות הפרטיות של צרפתי דגים מעושנים.", body, active=None)


# ---------------------------------------------------------------- misc outputs
def build_redirects():
    for old, new in REDIRECTS.items():
        target = u(new)
        write(old, f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>הדף עבר</title>
<meta name="robots" content="noindex"><link rel="canonical" href="{SITE['url']}{new}">
<meta http-equiv="refresh" content="0; url={target}"></head><body><p>הדף עבר. <a href="{target}">המשך</a></p>
<script>location.replace({json.dumps(target)})</script></body></html>""")


def build_404():
    body = page_hero("הדף לא נמצא", "ייתכן שהקישור ישן או שהדף עבר מקום.") + f"""
<section class="section"><div class="narrow center">
<p>אפשר לחזור ל<a href="{u('/')}">דף הבית</a>, לעבור ל<a href="{u('/shop/')}">חנות</a> או לכתוב לנו ב<a href="https://wa.me/{SITE['whatsapp']}">וואטסאפ</a>.</p>
{''.join(f'<a class="chip" style="display:inline-block;margin:4px" href="{u(c[2])}">{E(c[1])}</a>' for c in CATS)}
</div></section>"""
    page("/404.html", "הדף לא נמצא", "הדף לא נמצא", body, noindex=True)


def build_static():
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    (OUT / "assets/js/config.js").write_text(
        "window.SARFATI = " + json.dumps({
            "base": BASE, "whatsapp": SITE["whatsapp"], "phone": SITE["phone"], "shipping": SITE["shipping"],
            "formEndpoint": SITE.get("formEndpoint", ""), "formAccessKey": SITE.get("formAccessKey", ""),
        }, ensure_ascii=False) + ";\n", encoding="utf-8")
    for extra in ("CNAME", ".nojekyll"):
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, OUT / extra)
    (OUT / ".nojekyll").touch()
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /cart/\n\nSitemap: {SITE['url']}/sitemap.xml\n", encoding="utf-8")


def build_sitemap():
    from urllib.parse import quote
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
    build_blog()
    build_cart()
    build_terms()
    build_404()
    build_redirects()
    build_sitemap()
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"Built {n} HTML files into {OUT.relative_to(ROOT)}/ (base path: '{BASE or '/'}')")


if __name__ == "__main__":
    main()
