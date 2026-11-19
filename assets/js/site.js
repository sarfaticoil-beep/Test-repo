/* Sarfati site script: navigation, cart, checkout, forms, shop filters. No dependencies. Multilingual. */
(function () {
  "use strict";
  var CFG = window.SARFATI || {};
  var T = CFG.t || {};
  var LANG = CFG.lang || "he";
  var CART_KEY = "sarfati_cart_v2";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function tr(key, vars) {
    var s = T[key] || "";
    Object.keys(vars || {}).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }
  function money(n) {
    var v = Math.round(n * 100) / 100;
    return "₪" + (v % 1 === 0 ? v.toLocaleString("en-US") : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- storage (fails safe) ---------- */
  function load() {
    try { var v = JSON.parse(localStorage.getItem(CART_KEY) || "[]"); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  var memoryCart = null;
  function getCart() { return memoryCart || (memoryCart = load()); }
  function saveCart(c) {
    memoryCart = c;
    try { localStorage.setItem(CART_KEY, JSON.stringify(c)); } catch (e) { /* private mode */ }
    renderCount();
    document.dispatchEvent(new CustomEvent("cart:change"));
  }
  function cartQty() { return getCart().reduce(function (a, i) { return a + i.qty; }, 0); }
  function cartTotal() { return getCart().reduce(function (a, i) { return a + i.qty * i.price; }, 0); }
  function renderCount() {
    var n = cartQty();
    $$(".cart-count").forEach(function (el) { el.textContent = n; el.setAttribute("data-count", n); });
  }

  // item: {id, vi, name, he, variant, heVariant, price, image, url}
  function addToCart(item, qty) {
    var cart = getCart().slice();
    var key = item.id + "|" + (item.vi == null ? "" : item.vi);
    var found = cart.find(function (i) { return i.key === key; });
    if (found) { found.qty = Math.min(99, found.qty + qty); found.price = item.price; }
    else cart.push(Object.assign({ key: key, qty: qty }, item));
    saveCart(cart);
    toast(T.added + item.name + (item.variant ? " (" + item.variant + ")" : ""));
  }

  var toastTimer;
  function toast(msg) {
    var t = $("#toast");
    if (!t) return;
    t.querySelector("span").textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("show"); }, 3200);
  }

  /* ---------- mobile drawer ---------- */
  function initDrawer() {
    var drawer = $("#drawer");
    if (!drawer) return;
    var lastFocus;
    function open() {
      lastFocus = document.activeElement;
      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      $$(".menu-toggle").forEach(function (b) { b.setAttribute("aria-expanded", "true"); });
      document.body.style.overflow = "hidden";
      var f = drawer.querySelector("button, a"); if (f) f.focus();
    }
    function close() {
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      $$(".menu-toggle").forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
      document.body.style.overflow = "";
      if (lastFocus) lastFocus.focus();
    }
    $$(".menu-toggle").forEach(function (b) { b.addEventListener("click", open); });
    $$("[data-close-drawer]", drawer).forEach(function (b) { b.addEventListener("click", close); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && drawer.classList.contains("open")) close(); });
  }

  /* ---------- language menu: close on outside click / Esc ---------- */
  function initLangSwitch() {
    var d = $(".lang-switch");
    if (!d) return;
    document.addEventListener("click", function (e) { if (d.open && !d.contains(e.target)) d.open = false; });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && d.open) { d.open = false; d.querySelector("summary").focus(); } });
  }

  /* ---------- add-to-cart buttons on cards ---------- */
  function initCardButtons() {
    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-add]");
      if (!b) return;
      e.preventDefault();
      addToCart({
        id: +b.dataset.add, vi: null, name: b.dataset.name, he: b.dataset.he, price: +b.dataset.price,
        image: b.dataset.image, url: b.dataset.url, variant: "", heVariant: ""
      }, 1);
    });
  }

  /* ---------- product page ---------- */
  function initProduct() {
    var box = $("[data-buy-box]");
    if (!box) return;
    var sel = $("select[name=variant]", box);
    var qtyInput = $("input[name=qty]", box);
    var priceEl = $("[data-price-display]");
    var addBtn = $("[data-add-product]", box);
    function current() {
      if (sel) {
        var o = sel.options[sel.selectedIndex];
        return { vi: +o.value, price: +o.dataset.price, variant: o.dataset.label, heVariant: o.dataset.heLabel, inStock: o.dataset.stock !== "0" };
      }
      return { vi: null, price: +box.dataset.price, variant: "", heVariant: "", inStock: box.dataset.stock !== "0" };
    }
    function sync() {
      var c = current();
      if (priceEl) priceEl.textContent = money(c.price);
      addBtn.disabled = !c.inStock;
      addBtn.textContent = c.inStock ? T.addToCart : T.outOfStock;
    }
    if (sel) sel.addEventListener("change", sync);
    $$("[data-qty]", box).forEach(function (b) {
      b.addEventListener("click", function () {
        qtyInput.value = Math.max(1, Math.min(99, (+qtyInput.value || 1) + (+b.dataset.qty)));
      });
    });
    addBtn.addEventListener("click", function () {
      var c = current();
      if (!c.inStock) return;
      addToCart({ id: +box.dataset.id, vi: c.vi, name: box.dataset.name, he: box.dataset.he, image: box.dataset.image,
        url: location.pathname, price: c.price, variant: c.variant, heVariant: c.heVariant },
        Math.max(1, Math.min(99, +qtyInput.value || 1)));
    });
    sync();

    var main = $("[data-gallery-main]");
    $$("[data-thumb]").forEach(function (t) {
      t.addEventListener("click", function () {
        main.src = t.dataset.thumb;
        $$("[data-thumb]").forEach(function (x) { x.setAttribute("aria-pressed", x === t ? "true" : "false"); });
      });
    });
  }

  /* ---------- shop filtering ---------- */
  function initShop() {
    var grid = $("[data-product-grid]");
    var search = $("#shop-search");
    var sort = $("#shop-sort");
    if (!grid || (!search && !sort)) return;
    var cards = $$(".p-card", grid);
    var count = $("[data-result-count]");
    var empty = $("[data-empty]");
    var kosherSel = $("#shop-kosher");
    function apply() {
      var q = (search && search.value || "").trim().toLowerCase();
      var k = kosherSel ? kosherSel.value : "";
      var shown = 0;
      cards.forEach(function (c) {
        var ok = (!q || c.dataset.search.indexOf(q) !== -1) && (!k || (" " + c.dataset.kosher + " ").indexOf(" " + k + " ") !== -1);
        c.hidden = !ok; if (ok) shown++;
      });
      var mode = sort ? sort.value : "default";
      var sorted = cards.slice().sort(function (a, b) {
        if (mode === "price-asc") return a.dataset.price - b.dataset.price;
        if (mode === "price-desc") return b.dataset.price - a.dataset.price;
        if (mode === "name") return a.dataset.name.localeCompare(b.dataset.name, LANG);
        return a.dataset.order - b.dataset.order;
      });
      sorted.forEach(function (c) { grid.appendChild(c); });
      if (count) count.textContent = tr("nProducts", { n: shown });
      if (empty) empty.hidden = shown !== 0;
    }
    [search, sort, kosherSel].forEach(function (el) { if (el) el.addEventListener("input", apply); });
    var params = new URLSearchParams(location.search);
    if (search && params.get("q")) search.value = params.get("q");
    apply();
  }

  /* ---------- cart page ---------- */
  function shippingFor(subtotal, method) {
    var s = CFG.shipping || {};
    if (method !== "delivery") return 0;
    return subtotal >= s.freeOver ? 0 : s.fee;
  }

  function initCartPage() {
    var root = $("[data-cart-page]");
    if (!root) return;
    var list = $("[data-cart-items]", root);
    var emptyEl = $("[data-cart-empty]", root);
    var filled = $("[data-cart-filled]", root);
    var form = $("#checkout-form");

    // refresh names, prices and stock from the live catalogue, in this page's language
    fetch(CFG.catalog).then(function (r) { return r.json(); }).then(function (products) {
      var map = {}; products.forEach(function (p) { map[p.id] = p; });
      var cart = getCart().filter(function (i) { return map[i.id]; }).map(function (i) {
        var p = map[i.id];
        i.name = p.name; i.he = p.he; i.url = p.url; i.image = i.image || p.image;
        if (i.vi != null && p.variants[i.vi]) {
          var v = p.variants[i.vi];
          i.price = v.price; i.variant = v.label; i.heVariant = v.he;
        } else if (!p.variants.length) i.price = p.price;
        return i;
      });
      saveCart(cart);
    }).catch(function () { render(); });

    function render() {
      var cart = getCart();
      emptyEl.hidden = cart.length > 0;
      filled.hidden = cart.length === 0;
      list.innerHTML = cart.map(function (i, idx) {
        return '<li class="cart-item">' +
          (i.image ? '<img src="' + esc(i.image) + '" alt="" width="76" height="76" loading="lazy">' : '<span></span>') +
          '<div><h3>' + (i.url ? '<a href="' + esc(i.url) + '">' + esc(i.name) + "</a>" : esc(i.name)) + "</h3>" +
          (i.variant ? '<div class="variant">' + esc(i.variant) + "</div>" : "") +
          '<div class="variant">' + money(i.price) + esc(T.perUnit) + "</div>" +
          '<div class="qty" style="margin-top:6px"><button type="button" data-cq="' + idx + '" data-d="1" aria-label="+">+</button>' +
          '<input type="number" min="1" max="99" value="' + i.qty + '" data-ci="' + idx + '" aria-label="' + esc(T.qtyOf + i.name) + '">' +
          '<button type="button" data-cq="' + idx + '" data-d="-1" aria-label="−">−</button></div></div>' +
          '<div class="line-total">' + money(i.price * i.qty) + '<br><button type="button" class="remove" data-rm="' + idx + '">' + esc(T.remove) + "</button></div></li>";
      }).join("");
      renderSummary();
    }

    function method() { var m = form && form.querySelector("input[name=method]:checked"); return m ? m.value : "delivery"; }

    function renderSummary() {
      var s = CFG.shipping || {};
      var sub = cartTotal();
      var m = method();
      var ship = shippingFor(sub, m);
      $("[data-sub]").textContent = money(sub);
      $("[data-ship]").textContent = m === "delivery" ? (ship === 0 ? T.free : money(ship)) : T.pickupFree;
      $("[data-total]").textContent = money(sub + ship);
      var bar = $("[data-free-bar]"), msg = $("[data-free-msg]");
      if (m === "delivery") {
        bar.parentElement.hidden = false;
        bar.style.width = Math.min(100, sub / s.freeOver * 100) + "%";
        msg.textContent = sub >= s.freeOver ? T.freeYes :
          sub < s.minOrder ? tr("minMsg", { min: money(s.minOrder), left: money(s.minOrder - sub) }) :
          tr("toFree", { left: money(s.freeOver - sub) });
      } else { bar.parentElement.hidden = true; msg.textContent = ""; }
      var submit = $("[data-submit-order]");
      if (submit) submit.disabled = getCart().length === 0;
      $$("[data-delivery-only]").forEach(function (el) {
        el.hidden = m !== "delivery";
        $$("input, select", el).forEach(function (f) { f.required = m === "delivery" && f.hasAttribute("data-req"); });
      });
    }

    list.addEventListener("click", function (e) {
      var cart = getCart().slice();
      var b = e.target.closest("[data-cq]");
      if (b) { var i = cart[+b.dataset.cq]; i.qty = Math.max(1, Math.min(99, i.qty + (+b.dataset.d))); saveCart(cart); return; }
      var r = e.target.closest("[data-rm]");
      if (r) { cart.splice(+r.dataset.rm, 1); saveCart(cart); }
    });
    list.addEventListener("change", function (e) {
      var inp = e.target.closest("[data-ci]"); if (!inp) return;
      var cart = getCart().slice(); cart[+inp.dataset.ci].qty = Math.max(1, Math.min(99, +inp.value || 1)); saveCart(cart);
    });
    document.addEventListener("cart:change", render);
    if (form) {
      prefillDetails(form);
      form.addEventListener("change", renderSummary);
      var dateInput = form.querySelector("input[type=date]");
      if (dateInput) {
        var t = new Date(); t.setDate(t.getDate() + 1);
        dateInput.min = t.toISOString().slice(0, 10);
      }
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var cart = getCart();
        var s = CFG.shipping;
        var sub = cartTotal(), m = method();
        var status = $(".form-status", form);
        status.className = "form-status";
        if (!cart.length) return;
        if (m === "delivery" && sub < s.minOrder) {
          status.className = "form-status err";
          status.textContent = tr("minErr", { min: money(s.minOrder) });
          return;
        }
        if (!form.reportValidity()) return;
        var fd = new FormData(form);
        rememberDetails(form);
        var via = e.submitter && e.submitter.dataset.pay;
        if (CFG.payments && via !== "wa") { payByCard(fd, m, status); return; }
        var ship = shippingFor(sub, m);
        var methodLabel = { delivery: T.mDelivery, shilat: T.mShilat, sarona: T.mSarona }[m];
        var lines = ["*" + T.orderTitle + "*" + (LANG !== "he" ? " [" + LANG.toUpperCase() + "]" : ""), ""];
        cart.forEach(function (i) {
          var line = "• " + i.name + (i.variant ? " (" + i.variant + ")" : "") + " × " + i.qty + " = " + money(i.price * i.qty);
          if (LANG !== "he" && i.he) line += "\n   ↳ " + i.he + (i.heVariant ? " (" + i.heVariant + ")" : "");
          lines.push(line);
        });
        lines.push("", T.lSubtotal + ": " + money(sub));
        lines.push(T.lShipping + ": " + (m === "delivery" ? (ship ? money(ship) : T.free) : "—"));
        lines.push("*" + T.lTotal + ": " + money(sub + ship) + "*", "");
        lines.push(T.lName + ": " + fd.get("name"), T.lPhone + ": " + fd.get("phone"));
        if (fd.get("email")) lines.push(T.lEmail + ": " + fd.get("email"));
        lines.push(T.lMethod + ": " + methodLabel);
        if (m === "delivery") {
          var zoneSel = form.querySelector("select[name=zone]");
          lines.push(T.lZone + ": " + zoneSel.options[zoneSel.selectedIndex].text);
          lines.push(T.lAddress + ": " + fd.get("address") + ", " + fd.get("city"));
        }
        if (fd.get("date")) lines.push(T.lDate + ": " + fd.get("date"));
        if (fd.get("notes")) lines.push(T.lNotes + ": " + fd.get("notes"));
        var text = lines.join("\n");
        sendToEndpoint(T.orderTitle, text, fd);
        var url = "https://wa.me/" + CFG.whatsapp + "?text=" + encodeURIComponent(text);
        status.className = "form-status ok";
        status.innerHTML = tr("orderReady", { url: url });
        window.open(url, "_blank", "noopener");
        $("[data-clear-after]").hidden = false;
      });
    }
    var clear = $("[data-clear-cart]");
    if (clear) clear.addEventListener("click", function () { saveCart([]); $("[data-clear-after]").hidden = true; });

    // coming back from the payment page
    var params = new URLSearchParams(location.search);
    if (params.get("paid") === "1") {
      saveCart([]);
      var paid = $("[data-paid]", root); paid.hidden = false;
      $("[data-order-ref]", root).textContent = params.get("order") || "";
      paid.scrollIntoView({ block: "center" });
    } else if (params.get("failed") === "1") {
      $("[data-failed]", root).hidden = false;
    }
    render();
  }

  /* ---------- "remember my details" (stored only in this browser) ---------- */
  var DETAILS_KEY = "sarfati_customer_v1";
  var DETAIL_FIELDS = ["name", "phone", "email", "zone", "city", "address"];

  function prefillDetails(form) {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(DETAILS_KEY) || "null"); } catch (e) { saved = null; }
    if (!saved) return;
    DETAIL_FIELDS.forEach(function (k) {
      var f = form.elements[k];
      if (f && saved[k] && (f.tagName === "SELECT" || !f.value)) f.value = saved[k];
    });
    if (saved.method && form.querySelector('input[name=method][value="' + saved.method + '"]')) {
      form.querySelector('input[name=method][value="' + saved.method + '"]').checked = true;
    }
    var box = form.querySelector("[data-remember]");
    if (box) box.checked = true;
    var note = form.querySelector("[data-prefilled]");
    if (note) note.hidden = false;
    var forget = form.querySelector("[data-forget]");
    if (forget) forget.addEventListener("click", function () {
      try { localStorage.removeItem(DETAILS_KEY); } catch (e) { /* ignore */ }
      DETAIL_FIELDS.forEach(function (k) { if (form.elements[k] && k !== "zone") form.elements[k].value = ""; });
      if (box) box.checked = false;
      note.hidden = true;
    });
  }

  function rememberDetails(form) {
    var box = form.querySelector("[data-remember]");
    try {
      if (box && box.checked) {
        var data = { method: (form.querySelector("input[name=method]:checked") || {}).value };
        DETAIL_FIELDS.forEach(function (k) { if (form.elements[k]) data[k] = form.elements[k].value; });
        localStorage.setItem(DETAILS_KEY, JSON.stringify(data));
      } else {
        localStorage.removeItem(DETAILS_KEY);
      }
    } catch (e) { /* private mode: nothing saved */ }
  }

  function payByCard(fd, method, status) {
    var btns = $$("#checkout-form [type=submit]");
    btns.forEach(function (b) { b.disabled = true; });
    status.className = "form-status ok";
    status.textContent = T.paying;
    var payload = {
      lang: LANG, method: method,
      items: getCart().map(function (i) { return { id: i.id, vi: i.vi, qty: i.qty }; }),
      customer: {
        name: fd.get("name"), phone: fd.get("phone"), email: fd.get("email"), zone: fd.get("zone"),
        city: fd.get("city"), address: fd.get("address"), date: fd.get("date"), notes: fd.get("notes")
      }
    };
    fetch(CFG.checkoutUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok && res.d.url) { location.href = res.d.url; return; }
        throw res.d.error || "error";
      })
      .catch(function (err) {
        btns.forEach(function (b) { b.disabled = false; });
        status.className = "form-status err";
        status.textContent = err === "item_unavailable" ? T.unavailable : T.payError;
      });
  }

  /* ---------- generic forms (contact / events / club / business) ---------- */
  function sendToEndpoint(subject, text, fd) {
    if (!CFG.formEndpoint) return Promise.resolve(false);
    var body = { subject: subject, message: text, from_name: "Sarfati website", language: LANG };
    if (CFG.formAccessKey) body.access_key = CFG.formAccessKey;
    if (fd) fd.forEach(function (v, k) { if (!(k in body)) body[k] = v; });
    return fetch(CFG.formEndpoint, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body)
    }).then(function (r) { return r.ok; }).catch(function () { return false; });
  }

  function initForms() {
    $$("form[data-form]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!form.reportValidity()) return;
        var title = form.dataset.form;
        var fd = new FormData(form);
        var lines = ["*" + title + T.fromSite + "*" + (LANG !== "he" ? " [" + LANG.toUpperCase() + "]" : "")];
        $$("[name]", form).forEach(function (f) {
          if (f.type === "checkbox" || f.type === "hidden" || !f.value) return;
          var lab = form.querySelector('label[for="' + f.id + '"]');
          lines.push((lab ? lab.textContent.replace(/\s*\*$/, "") : f.name) + ": " + f.value);
        });
        var text = lines.join("\n");
        var status = $(".form-status", form);
        var btn = form.querySelector("[type=submit]");
        btn.disabled = true;
        sendToEndpoint(title, text, fd).then(function (ok) {
          btn.disabled = false;
          if (ok) {
            status.className = "form-status ok";
            status.textContent = T.thanks;
            form.reset();
          } else {
            var url = "https://wa.me/" + CFG.whatsapp + "?text=" + encodeURIComponent(text);
            status.className = "form-status ok";
            status.innerHTML = tr("almost", { url: url });
            window.open(url, "_blank", "noopener");
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderCount();
    initDrawer();
    initLangSwitch();
    initCardButtons();
    initProduct();
    initShop();
    initCartPage();
    initForms();
    $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });
  });
  window.addEventListener("storage", function (e) { if (e.key === CART_KEY) { memoryCart = null; renderCount(); document.dispatchEvent(new CustomEvent("cart:change")); } });
})();
