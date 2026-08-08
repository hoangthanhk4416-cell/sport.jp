(() => {
 "use strict";

 const config = window.TEAMSPIRIT_ORDER_CONFIG || {};
 const sizes = ["55 (XS)","60 (S)","65 (M)","70 (L)","75 (XL)","80 (2XL)","85 (3XL)","90","95","100","105","110","Khác"];
 const colors = [
 { label: "既存デザインのまま", value: "Giữ nguyên thiết kế" },
 { label: "カラー変更を希望", value: "Màu sắc tùy chỉnh" },
 ];
 const contacts = ["Instagram","LINE","Điện thoại"];
 let selectedProduct = null;
 let cartOrderItems = [];
 let orderMode = "single";
 let currentStep = 1;

 const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
 "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[char]));
 const normalizeSize = value => {
 const text = String(value || "").trim().replace(/\b(lít|lit|liters?|litres?)\b/gi, "L");
 const match = text.match(/^(\d+)\s*\(?\s*(XS|S|M|L|XL|2XL|3XL|4XL)\s*\)?$/i);
 return match ? `${match[1]} (${match[2].toUpperCase()})` : text;
 };
 const numericPrice = value => {
 const digits = String(value || "").replace(/[^\d]/g, "");
 return digits ? Number(digits) : 0;
 };
 const productIdFromUrl = url => {
 const match = String(url || "").match(/\/products\/([^/?#]+)/);
 return match ? match[1] : "";
 };
 const currentProduct = () => {
 const title = document.querySelector(".product-info h1");
 if (!title) return null;
 const canonical = document.querySelector('link[rel="canonical"]')?.href || location.href;
 return {
 id: productIdFromUrl(canonical) || location.pathname.split("/").filter(Boolean).pop(),
 name: title.textContent.trim(),
 price: document.querySelector(".product-info .current-price")?.textContent.trim() || "",
 image: document.querySelector("#productMainImage,.product-gallery-main img")?.src || "",
 url: canonical,
 };
 };
 const productFromCard = card => {
 const link = card.querySelector('a[href*="/products/"]');
 const inlineOpen = card.querySelector("[onclick*='openProduct']")?.getAttribute("onclick") || "";
 const id = productIdFromUrl(link?.href) || inlineOpen.match(/openProduct\(['"]([^'"]+)/)?.[1] || "";
 const catalogProduct = window.SITE_DATA?.products?.find(product => product.id === id);
 return {
 id,
 name: catalogProduct?.name || card.querySelector(".name,h2")?.textContent.trim() || id,
 price: catalogProduct?.price || card.querySelector(".price,.current-price")?.textContent.trim() || "",
 image: catalogProduct?.image || card.querySelector("img")?.src || "",
 url: link?.href || `${location.origin}/products/${id}/`,
 };
 };

 function ensureModal() {
 if (document.getElementById("tsOrderModal")) return;
 document.body.insertAdjacentHTML("beforeend", `
 <div class="ts-order-modal" id="tsOrderModal" hidden>
 <section class="ts-order-dialog" role="dialog" aria-modal="true" aria-labelledby="tsOrderTitle">
 <header class="ts-order-head">
 <h2 id="tsOrderTitle">TEAMSPIRIT-jpで注文</h2>
 <button class="ts-order-close" type="button" aria-label="閉じる">×</button>
 </header>
 <div class="ts-order-body" id="tsOrderBody"></div>
 <footer class="ts-order-actions" id="tsOrderActions"></footer>
 </section>
 </div>`);
 const modal = document.getElementById("tsOrderModal");
 modal.querySelector(".ts-order-close").addEventListener("click", closeModal);
 modal.addEventListener("click", event => { if (event.target === modal) closeModal(); });
 document.addEventListener("keydown", event => {
 if (event.key === "Escape" && !modal.hidden) closeModal();
 });
 }

 function progress(step) {
 return `<div class="ts-order-progress"><span class="${step === 1 ? "active" : ""}">1. 商品 </span><span class="${step === 2 ? "active" : ""}">2. 配送情報</span></div>`;
 }

 function renderStepOne() {
 if (orderMode === "cart") {
 renderCartStepOne();
 return;
 }
 currentStep = 1;
 const body = document.getElementById("tsOrderBody");
 const existingSize = normalizeSize(document.querySelector(".product-size.active")?.dataset.size || "");
 body.innerHTML = `${progress(1)}
 <div class="ts-order-product">
 <img src="${escapeHtml(selectedProduct.image)}" alt="">
 <div><strong>${escapeHtml(selectedProduct.name)}</strong><span>${escapeHtml(selectedProduct.price || "価格はお問い合わせください")}</span></div>
 </div>
 <div class="ts-order-grid">
 <div class="ts-order-field"><label for="tsSize">サイズ *</label><select id="tsSize" translate="no" required><option value="">サイズを選択</option>${sizes.map(size => `<option value="${escapeHtml(size)}" translate="no" ${size === existingSize ? "selected" : ""}>${escapeHtml(size)}</option>`).join("")}</select></div>
 <div class="ts-order-field"><label for="tsColor">カラー *</label><select id="tsColor" required><option value="">カラーを選択</option>${colors.map(color => `<option value="${escapeHtml(color.value)}">${escapeHtml(color.label)}</option>`).join("")}</select></div>
 <div class="ts-order-field"><label for="tsQuantity">数量 *</label><input id="tsQuantity" type="number" min="1" max="999" value="${escapeHtml(document.getElementById("productQuantity")?.value || 1)}" inputmode="numeric" required></div>
 <div class="ts-order-field"><label for="tsJerseyNumber">背番号</label><input id="tsJerseyNumber" maxlength="3" placeholder="例：10"></div>
 <div class="ts-order-field"><label for="tsPrintName">マーキング名</label><input id="tsPrintName" maxlength="30" placeholder="名前または文字を入力"></div>
 <div class="ts-order-field full"><label for="tsDesignRequest">制作に関するご要望</label><textarea id="tsDesignRequest" maxlength="1000" placeholder="希望する 変更 入力 Instagram LINE 相談 こと あります."></textarea></div>
 </div>
 <p class="ts-order-note">制作前にTEAMSPIRIT-jpの担当者がデザイン、最終金額、制作日程を確認します。</p>
 <p class="ts-order-status" id="tsOrderStatus" role="status" aria-live="polite"></p>`;
 document.getElementById("tsOrderActions").innerHTML = `<button class="ts-order-secondary" type="button" data-action="cancel">キャンセル</button><button class="ts-order-primary" type="button" data-action="continue">注文手続きへ</button>`;
 bindActions();
 }

 function collectStepOne() {
 if (orderMode === "cart") return collectCartStepOne();
 const size = normalizeSize(document.getElementById("tsSize").value);
 const colorSelect = document.getElementById("tsColor");
 const color = colorSelect.value;
 const colorLabel = colorSelect.selectedOptions[0]?.textContent || color;
 const quantity = Math.max(1, Math.min(999, Number(document.getElementById("tsQuantity").value) || 0));
 if (!size || !color || !quantity) {
 document.getElementById("tsOrderStatus").textContent = "サイズ、カラー、数量を選択してください。";
 return false;
 }
 selectedProduct = {
 ...selectedProduct,
 size,
 color,
 colorLabel,
 quantity,
 printName: document.getElementById("tsPrintName").value.trim(),
 jerseyNumber: document.getElementById("tsJerseyNumber").value.trim(),
 designRequest: document.getElementById("tsDesignRequest").value.trim(),
 unitPrice: numericPrice(selectedProduct.price),
 };
 return true;
 }

 function renderCartStepOne() {
 currentStep = 1;
 const body = document.getElementById("tsOrderBody");
 body.innerHTML = `${progress(1)}
 <div class="ts-cart-order-list">
 ${cartOrderItems.map((item, index) => `
 <article class="ts-cart-order-item">
 <div class="ts-order-product">
 <img src="${escapeHtml(item.image)}" alt="">
 <div><strong>${escapeHtml(item.name)}</strong><span><span translate="no">${escapeHtml(normalizeSize(item.size))}</span> · ${escapeHtml(item.quantity)}</span></div>
 </div>
 <div class="ts-order-field">
 <label for="tsCartColor${index}">カラー *</label>
 <select id="tsCartColor${index}" data-cart-color="${index}" required>
 <option value="">カラーを選択</option>
 ${colors.map(color => `<option value="${escapeHtml(color.value)}">${escapeHtml(color.label)}</option>`).join("")}
 </select>
 </div>
 </article>`).join("")}
 </div>
 <div class="ts-order-grid">
 <div class="ts-order-field"><label for="tsJerseyNumber">背番号</label><input id="tsJerseyNumber" maxlength="3" placeholder="例：10"></div>
 <div class="ts-order-field"><label for="tsPrintName">マーキング名</label><input id="tsPrintName" maxlength="30" placeholder="名前または文字を入力"></div>
 <div class="ts-order-field full"><label for="tsDesignRequest">制作に関するご要望</label><textarea id="tsDesignRequest" maxlength="1000" placeholder="希望する 変更 入力 Instagram LINE 相談 こと あります."></textarea></div>
 </div>
 <p class="ts-order-note">各商品のカラーを選択してください。 制作前にTEAMSPIRIT-jpの担当者がデザイン、最終金額、制作日程を確認します。</p>
 <p class="ts-order-status" id="tsOrderStatus" role="status" aria-live="polite"></p>`;
 document.getElementById("tsOrderActions").innerHTML = `<button class="ts-order-secondary" type="button" data-action="cancel">キャンセル</button><button class="ts-order-primary" type="button" data-action="continue">注文手続きへ</button>`;
 bindActions();
 }

 function collectCartStepOne() {
 const printName = document.getElementById("tsPrintName").value.trim();
 const jerseyNumber = document.getElementById("tsJerseyNumber").value.trim();
 const designRequest = document.getElementById("tsDesignRequest").value.trim();
 let valid = true;
 cartOrderItems = cartOrderItems.map((item, index) => {
 const colorSelect = document.querySelector(`[data-cart-color="${index}"]`);
 const color = colorSelect?.value || "";
 if (!color) valid = false;
 return {
 ...item,
 size: normalizeSize(item.size),
 color,
 colorLabel: colorSelect?.selectedOptions[0]?.textContent || color,
 printName,
 jerseyNumber,
 designRequest,
 unitPrice: numericPrice(item.price),
 };
 });
 if (!valid) {
 document.getElementById("tsOrderStatus").textContent = "すべての商品のカラーを選択してください。";
 return false;
 }
 return true;
 }

 function renderStepTwo() {
 if (!collectStepOne()) return;
 currentStep = 2;
 const productSummary = orderMode === "cart"
 ? `<div class="ts-cart-order-review">${cartOrderItems.map(item => `
 <div class="ts-order-product">
 <img src="${escapeHtml(item.image)}" alt="">
 <div><strong>${escapeHtml(item.name)}</strong><span><span translate="no">${escapeHtml(item.size)}</span> · ${escapeHtml(item.colorLabel || item.color)} · ${item.quantity}</span></div>
 </div>`).join("")}</div>`
 : `<div class="ts-order-product">
 <img src="${escapeHtml(selectedProduct.image)}" alt="">
 <div><strong>${escapeHtml(selectedProduct.name)}</strong><span><span translate="no">${escapeHtml(selectedProduct.size)}</span> · ${escapeHtml(selectedProduct.colorLabel || selectedProduct.color)} · ${selectedProduct.quantity}</span></div>
 </div>`;
 document.getElementById("tsOrderBody").innerHTML = `${progress(2)}
 ${productSummary}
 <div class="ts-order-grid">
 <div class="ts-order-field"><label for="tsCustomerName">お名前 *</label><input id="tsCustomerName" autocomplete="name" maxlength="80" required></div>
 <div class="ts-order-field"><label for="tsPhone">電話番号 *</label><input id="tsPhone" type="tel" autocomplete="tel" inputmode="tel" maxlength="24" placeholder="010-0000-0000" required></div>
 <div class="ts-order-field full"><label for="tsAddress">配送先住所</label><textarea id="tsAddress" autocomplete="street-address" maxlength="300"></textarea></div>
 <div class="ts-order-field full"><label for="tsContactChannel">希望する連絡方法（任意）</label><select id="tsContactChannel"><option value="">連絡を希望しない</option>${contacts.map(channel => `<option>${escapeHtml(channel)}</option>`).join("")}</select></div>
 </div>
 <p class="ts-order-status" id="tsOrderStatus" role="status" aria-live="polite"></p>`;
 document.getElementById("tsOrderActions").innerHTML = `<button class="ts-order-secondary" type="button" data-action="back">戻る</button><button class="ts-order-primary" type="button" data-action="submit">注文を確定</button>`;
 bindActions();
 }

 function validateCustomer() {
 const name = document.getElementById("tsCustomerName").value.trim();
 const phone = document.getElementById("tsPhone").value.trim();
 const address = document.getElementById("tsAddress").value.trim();
 const normalizedPhone = phone.replace(/\D/g, "");
 if (name.length < 2 || !/^0\d{8,10}$/.test(normalizedPhone)) {
 document.getElementById("tsOrderStatus").textContent = "お名前と正しい電話番号を入力してください。";
 return null;
 }
 return {
 name,
 phone: normalizedPhone,
 address: !address ? "Không cung cấp" : address.length < 8 ? `${address} (địa chỉ ngắn)` : address,
 contactChannel: document.getElementById("tsContactChannel").value || "Không yêu cầu",
 };
 }

 async function submitOrder(button) {
 const customer = validateCustomer();
 if (!customer) return;
 const endpoint = String(config.endpoint || "").trim();
 if (!endpoint || !/^https:\/\/script\.google\.com\//.test(endpoint)) {
 document.getElementById("tsOrderStatus").innerHTML = `オンライン注文はまだ有効になっていません。Google Sheetとの連携を完了してください。`;
 return;
 }
 button.disabled = true;
 button.textContent = "送信中…";
 const orderId = `TS-${new Date().toISOString().slice(0,10).replaceAll("-","")}-${crypto.getRandomValues(new Uint32Array(1))[0].toString(36).toUpperCase().slice(0,6)}`;
 const orderItems = orderMode === "cart" ? cartOrderItems : [selectedProduct];
 const payload = {
 orderId,
 submittedAt: new Date().toISOString(),
 customer,
 items: orderItems.map(item => ({
 ...item,
 lineTotal: item.unitPrice * item.quantity,
 })),
 source: "Website",
 pageUrl: location.href,
 userAgent: navigator.userAgent,
 };
 try {
 const response = await fetch(endpoint, {
 method: "POST",
 headers: { "Content-Type": "text/plain;charset=utf-8" },
 body: JSON.stringify(payload),
 });
 const result = await response.json();
 if (!response.ok || result.ok !== true) throw new Error(result.error || "注文を保存できませんでした。");
 if (orderMode === "cart") {
 localStorage.removeItem("teamspirit_cart_v1");
 window.dispatchEvent(new CustomEvent("teamspirit:cart-order-success"));
 }
 document.getElementById("tsOrderBody").innerHTML = `<div class="ts-order-success"><div class="ts-order-success-mark">✓</div><h3>ご注文を受け付けました</h3><p> 注文番号 制作・配送状況をご確認いただけます。</p><div class="ts-order-code"><strong>${escapeHtml(orderId)}</strong><button type="button" data-action="copy-order" data-order-id="${escapeHtml(orderId)}">注文番号 コピー</button></div><p>TEAMSPIRIT-jpの担当者がデザインと配送情報の確認のためご連絡します。</p></div>`;
 document.getElementById("tsOrderActions").innerHTML = `<button class="ts-order-secondary" type="button" data-action="done">閉じる</button><button class="ts-order-primary" type="button" data-action="track-order" data-order-id="${escapeHtml(orderId)}">注文を照会する</button>`;
 bindActions();
 } catch (error) {
 const message = error.message === "Thiếu địa chỉ"
 ? "Địa chỉ không bắt buộc. Vui lòng thử gửi lại đơn hàng"
 : error.message;
 document.getElementById("tsOrderStatus").textContent = `Không thể gửi đơn hàng: ${message}. Vui lòng thử lại hoặc liên hệ qua LINE.`;
 button.disabled = false;
 button.textContent = "注文を確定";
 }
 }

 function bindActions() {
 document.getElementById("tsOrderActions").querySelectorAll("[data-action]").forEach(button => {
 button.addEventListener("click", () => {
 if (button.dataset.action === "cancel" || button.dataset.action === "done") closeModal();
 if (button.dataset.action === "continue") renderStepTwo();
 if (button.dataset.action === "back") renderStepOne();
 if (button.dataset.action === "submit") submitOrder(button);
 if (button.dataset.action === "track-order") location.href = `/pages/orders/?orderId=${encodeURIComponent(button.dataset.orderId)}`;
 });
 });
 document.getElementById("tsOrderBody").querySelectorAll("[data-action='copy-order']").forEach(button => {
 button.addEventListener("click", async () => {
 const orderId = button.dataset.orderId || "";
 try {
 await navigator.clipboard.writeText(orderId);
 } catch (_error) {
 const temporary = document.createElement("textarea");
 temporary.value = orderId;
 document.body.appendChild(temporary);
 temporary.select();
 document.execCommand("copy");
 temporary.remove();
 }
 button.textContent = "コピーしました";
 });
 });
 }

 function openModal(product) {
 if (!product?.id) return;
 ensureModal();
 orderMode = "single";
 cartOrderItems = [];
 selectedProduct = product;
 document.getElementById("tsOrderModal").hidden = false;
 document.body.style.overflow = "hidden";
 renderStepOne();
 }

 function storedCartProducts() {
 let storedItems = [];
 try {
 storedItems = JSON.parse(localStorage.getItem("teamspirit_cart_v1")) || [];
 } catch (_error) {
 storedItems = [];
 }
 const catalog = Array.isArray(window.SITE_DATA?.products) ? window.SITE_DATA.products : [];
 const detailProduct = currentProduct();
 return storedItems.map(item => {
 const product = catalog.find(entry => entry.id === item.id)
 || (detailProduct?.id === item.id ? detailProduct : null)
 || {};
 return {
 id: item.id,
 name: product.name || item.name || item.id,
 price: product.price || item.price || "",
 image: product.image || item.image || "",
 url: product.url || item.url || `${location.origin}/products/${item.id}/`,
 size: normalizeSize(item.size),
 quantity: Math.max(1, Number(item.quantity) || 1),
 };
 }).filter(item => item.id && item.size);
 }

 function openCartOrder(items) {
 const preparedItems = Array.isArray(items) ? items.filter(item => item?.id && item?.size) : [];
 if (!preparedItems.length) {
 window.showFloatingToast?.("カートは空です。");
 return;
 }
 ensureModal();
 orderMode = "cart";
 selectedProduct = null;
 cartOrderItems = preparedItems.map(item => ({ ...item }));
 ["cartModal", "seoCartModal"].forEach(id => {
 const modal = document.getElementById(id);
 if (modal) modal.hidden = true;
 });
 document.getElementById("tsOrderModal").hidden = false;
 document.body.style.overflow = "hidden";
 renderStepOne();
 }

 window.openTeamspiritCartOrder = openCartOrder;
 window.openTeamspiritStoredCartOrder = () => openCartOrder(storedCartProducts());

 function closeModal() {
 const modal = document.getElementById("tsOrderModal");
 if (modal) modal.hidden = true;
 document.body.style.overflow = "";
 }

 function enhanceProducts() {
 const detailProduct = currentProduct();
 const productInfo = document.querySelector(".product-info");
 if (detailProduct && productInfo && !productInfo.querySelector(".ts-order-button")) {
 const button = document.createElement("button");
 button.type = "button";
 button.className = "ts-order-button";
 button.textContent = "注文・無料サンプル";
 button.addEventListener("click", () => openModal(currentProduct()));
 const actions = productInfo.querySelector(".contact-order-actions");
 productInfo.insertBefore(button, actions || null);
 }
 document.querySelectorAll(".card,.product-card").forEach(card => {
 if (card.querySelector(".ts-order-button")) return;
 const product = productFromCard(card);
 if (!product.id) return;
 const button = document.createElement("button");
 button.type = "button";
 button.className = "ts-order-button";
 button.textContent = "注文・無料サンプル";
 button.addEventListener("click", event => {
 event.preventDefault();
 event.stopPropagation();
 openModal(productFromCard(card));
 });
 card.appendChild(button);
 });
 document.querySelectorAll(".seo-cart-panel .contact-order-actions").forEach(actions => {
 if (actions.querySelector(".ts-cart-checkout")) return;
 const button = document.createElement("button");
 button.type = "button";
 button.className = "ts-cart-checkout";
 button.textContent = "注文する";
 button.addEventListener("click", window.openTeamspiritStoredCartOrder);
 actions.insertBefore(button, actions.firstChild);
 });
 }

 function init() {
 ensureModal();
 enhanceProducts();
 const observer = new MutationObserver(enhanceProducts);
 observer.observe(document.body, { childList: true, subtree: true });
 }

 if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
 else init();
})();
