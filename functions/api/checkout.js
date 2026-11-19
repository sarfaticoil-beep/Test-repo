/**
 * POST /api/checkout  –  Cloudflare Pages Function
 *
 * Receives the cart from the browser, recalculates every price from the site's own catalogue
 * (never trusts prices sent by the browser), and asks Rivhit iCredit for a secure payment page.
 * Returns { url } – the browser then redirects the customer to iCredit to pay.
 *
 * Settings (Cloudflare Pages → Settings → Variables and secrets):
 *   ICREDIT_TOKEN      (secret) GroupPrivateToken of the iCredit payment page, from Rivhit
 *   ICREDIT_SANDBOX    "1" = Rivhit test server (testicredit), "0" = real payments
 *   ICREDIT_SALE_TYPE  "1" = charge immediately, "2" = J5 hold (charge the final amount after weighing)
 *   ORDER_EMAIL        business e-mail that receives a copy of every paid order
 */

const METHODS = { delivery: "משלוח עד הבית", shilat: "איסוף מחנות המפעל בשילת", sarona: "איסוף משרונה מרקט" };
const ZONES = {
  south: "שני (אחת לשבועיים) – אשדוד, אשקלון, קריית גת",
  sharon: "שלישי – השרון וגוש דן",
  jerusalem: "רביעי – ירושלים והסביבה",
  telaviv: "חמישי – תל אביב–יפו",
  other: "בתיאום טלפוני – אזור אחר",
};
const LANGS = ["he", "en", "fr", "ru", "ar"];

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });
}

function clean(v, max = 200) {
  return String(v == null ? "" : v).replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max);
}

export async function onRequestPost({ request, env }) {
  if (!env.ICREDIT_TOKEN) return json({ error: "payments_not_configured" }, 503);

  let body;
  try { body = await request.json(); } catch (e) { return json({ error: "bad_request" }, 400); }

  const lang = LANGS.includes(body.lang) ? body.lang : "he";
  const method = METHODS[body.method] ? body.method : null;
  const c = body.customer || {};
  const name = clean(c.name, 80), phone = clean(c.phone, 20);
  if (!method || !name || !/^[0-9+\-\s]{9,15}$/.test(phone)) return json({ error: "missing_details" }, 400);
  if (method === "delivery" && (!ZONES[c.zone] || !clean(c.city) || !clean(c.address))) return json({ error: "missing_address" }, 400);
  if (!Array.isArray(body.items) || !body.items.length || body.items.length > 60) return json({ error: "empty_cart" }, 400);

  // Load the catalogue from the deployed site itself
  const base = new URL(request.url);
  const catRes = await env.ASSETS.fetch(new URL((env.BASE_PATH || "") + "/assets/data/catalog-he.json", base));
  if (!catRes.ok) return json({ error: "catalog_unavailable" }, 500);
  const rulesRes = await env.ASSETS.fetch(new URL((env.BASE_PATH || "") + "/assets/data/shop-rules.json", base));
  if (!rulesRes.ok) return json({ error: "rules_unavailable" }, 500);
  const SHIPPING = await rulesRes.json();
  const catalog = {};
  (await catRes.json()).forEach((p) => { catalog[p.id] = p; });

  const items = [];
  let subtotal = 0;
  for (const it of body.items) {
    const p = catalog[it.id];
    const qty = Math.floor(Number(it.qty));
    if (!p || !p.inStock || !(qty >= 1 && qty <= 99)) return json({ error: "item_unavailable", id: it.id }, 409);
    let price = p.price, label = p.he;
    if (p.variants && p.variants.length) {
      const v = p.variants[Number(it.vi)];
      if (!v || !v.inStock) return json({ error: "item_unavailable", id: it.id }, 409);
      price = v.price;
      label = `${p.he} (${v.he})`;
    }
    subtotal += price * qty;
    items.push({ Id: 0, CatalogNumber: String(p.id), UnitPrice: price, Quantity: qty, Description: label.slice(0, 100) });
  }
  subtotal = Math.round(subtotal * 100) / 100;

  if (method === "delivery") {
    if (subtotal < SHIPPING.minOrder) return json({ error: "below_minimum", min: SHIPPING.minOrder }, 400);
    if (subtotal < SHIPPING.freeOver) items.push({ Id: 0, CatalogNumber: "SHIP", UnitPrice: SHIPPING.fee, Quantity: 1, Description: "משלוח בקירור" });
  }

  const ref = "W" + Date.now().toString(36).toUpperCase();
  const prefix = (env.BASE_PATH || "") + (lang === "he" ? "" : "/" + lang);
  const cartUrl = `${base.origin}${prefix}/cart/`;
  const [first, ...rest] = name.split(/\s+/);
  const delivery = method === "delivery" ? `${METHODS[method]} – ${ZONES[c.zone]}` : METHODS[method];

  const payload = {
    GroupPrivateToken: env.ICREDIT_TOKEN,
    Items: items,
    Currency: 1,                                   // ILS
    SaleType: env.ICREDIT_SALE_TYPE === "2" ? 2 : 1, // 1 charge, 2 J5 / authorize only
    DocumentLanguage: lang === "he" ? "he" : "en",
    RedirectURL: `${cartUrl}?paid=1&order=${ref}`,
    FailRedirectURL: `${cartUrl}?failed=1`,
    Order: ref,
    CustomerFirstName: clean(first, 40),
    CustomerLastName: clean(rest.join(" "), 40) || clean(first, 40),
    PhoneNumber: phone,
    Address: method === "delivery" ? clean(c.address, 100) : "",
    City: method === "delivery" ? clean(c.city, 50) : "",
    Comments: clean(`${delivery}${c.date ? " | תאריך מבוקש: " + clean(c.date, 20) : ""}${c.notes ? " | הערות: " + clean(c.notes, 300) : ""}`, 500),
    Custom1: delivery.slice(0, 100),
    Custom2: clean(c.date, 20),
    Custom3: lang,
    MaxPayments: 1,
  };
  const email = clean(c.email, 100);
  if (email && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { payload.EmailAddress = email; payload.SendMail = true; }
  if (env.ORDER_EMAIL) payload.EmailBcc = env.ORDER_EMAIL;

  const host = env.ICREDIT_SANDBOX === "0" ? "icredit.rivhit.co.il" : "testicredit.rivhit.co.il";
  let res;
  try {
    res = await fetch(`https://${host}/API/PaymentPageRequest.svc/GetUrl`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
  } catch (e) {
    return json({ error: "gateway_unreachable" }, 502);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.Status !== 0 || !data.URL) {
    console.log("iCredit GetUrl failed", res.status, data.Status, data.DebugMessage);
    return json({ error: "gateway_error" }, 502);
  }
  return json({ url: data.URL, order: ref, total: subtotal });
}

export function onRequest() {
  return json({ error: "method_not_allowed" }, 405);
}
