(() => {
 "use strict";

 const config = window.TEAMSPIRIT_ORDER_CONFIG || {};
 const form = document.getElementById("orderLookupForm");
 const input = document.getElementById("orderLookupInput");
 const message = document.getElementById("trackingMessage");
 const results = document.getElementById("trackingResults");
 if (!form || !input || !message || !results) return;

 const statusLabels = {
 NEW: "受付済み",
 CONFIRMED: "注文確認",
 DESIGNING: "デザイン作業中",
 PRODUCTION: "制作中",
 SHIPPING: "配送中",
 COMPLETED: "完了",
 CANCELLED: "キャンセル",
 };
 const progressStatuses = ["NEW", "CONFIRMED", "DESIGNING", "PRODUCTION", "SHIPPING", "COMPLETED"];

 const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
 "&": "&amp;",
 "<": "&lt;",
 ">": "&gt;",
 '"': "&quot;",
 "'": "&#039;",
 })[character]);

 function lookupParameters(value) {
 const text = String(value || "").trim();
 if (/^TS-/i.test(text)) return { orderId: text.toUpperCase() };
 let phone = text.replace(/\D/g, "");
 if (/^82\d{9,10}$/.test(phone)) phone = `0${phone.slice(2)}`;
 if (!phone.startsWith("0") && /^\d{9,10}$/.test(phone)) phone = `0${phone}`;
 return phone ? { phone } : {};
 }

 function jsonpRequest(parameters) {
 const endpoint = String(config.endpoint || "").trim();
 if (!/^https:\/\/script\.google\.com\//.test(endpoint)) {
 return Promise.reject(new Error("注文照会サービスはまだ接続されていません。"));
 }

 return new Promise((resolve, reject) => {
 const callback = `__tsOrderLookup_${Date.now()}_${Math.random().toString(36).slice(2)}`;
 const script = document.createElement("script");
 const url = new URL(endpoint);
 url.searchParams.set("mode", "lookup");
 url.searchParams.set("callback", callback);
 Object.entries(parameters).forEach(([key, value]) => url.searchParams.set(key, value));

 const cleanup = () => {
 delete window[callback];
 script.remove();
 clearTimeout(timeout);
 };
 const timeout = setTimeout(() => {
 cleanup();
 reject(new Error("照会がタイムアウトしました。もう一度お試しください。"));
 }, 15000);

 window[callback] = data => {
 cleanup();
 resolve(data);
 };
 script.onerror = () => {
 cleanup();
 reject(new Error("注文照会サーバーに接続できません。"));
 };
 script.src = url.toString();
 document.head.appendChild(script);
 });
 }

 function displayError(error) {
 const translations = {
 "Vui lòng nhập mã đơn hàng hoặc số điện thoại": "注文番号または電話番号を入力してください。",
 "Mã đơn hàng không đúng định dạng": "注文番号の形式が正しくありません。",
 "Số điện thoại không đúng định dạng": "電話番号の形式が正しくありません。",
 };
 message.className = "tracking-message";
 message.textContent = translations[error.message] || error.message || "注文を照会できませんでした。";
 }

 function statusSteps(statusKey) {
 if (statusKey === "CANCELLED") return `<div class="status-badge cancelled">キャンセル済みの注文です</div>`;
 const activeIndex = Math.max(0, progressStatuses.indexOf(statusKey));
 return `<div class="status-steps">${progressStatuses.map((item, index) => `
 <div class="status-step ${index < activeIndex ? "done" : index === activeIndex ? "current" : ""}">
 ${escapeHtml(statusLabels[item])}
 </div>`).join("")}</div>`;
 }

 function formatPrice(value) {
 return `${new Intl.NumberFormat("ja-JP").format(Number(value || 0))}ウォン`;
 }

 function normalizeSize(value) {
 const text = String(value || "").trim().replace(/\b(lít|lit|liters?|litres?)\b/gi, "L");
 const match = text.match(/^(\d+)\s*\(?\s*(XS|S|M|L|XL|2XL|3XL|4XL)\s*\)?$/i);
 return match ? `${match[1]} (${match[2].toUpperCase()})` : text;
 }

 function koreanOptionLabel(value) {
 const text = String(value || "").trim().normalize("NFC");
 const options = {
 "giữ nguyên thiết kế": "既存デザインのまま",
 "màu sắc tùy chỉnh": "カラー変更を希望",
 "yêu cầu thiết kế riêng": "カラー変更を希望",
 "theo mẫu": "既存デザインのまま",
 "trắng": "カラー変更を希望",
 "đen": "カラー変更を希望",
 "đỏ": "カラー変更を希望",
 "xanh dương": "カラー変更を希望",
 "xanh lá": "カラー変更を希望",
 "vàng": "カラー変更を希望",
 "cam": "カラー変更を希望",
 "tím": "カラー変更を希望",
 "hồng": "カラー変更を希望",
 "khác": "カラー変更を希望",
 };
 return options[text.toLowerCase()] || text;
 }

 function formatSummary(value) {
 return String(value || "商品情報 確認 中").split(/\r?\n/).map(line => {
 const parts = line.split(/\s*\|\s*/);
 if (parts.length < 4) return escapeHtml(line);
 const [name, size, option, ...rest] = parts;
 return `${escapeHtml(name)} | <span translate="no">${escapeHtml(normalizeSize(size))}</span> | ${escapeHtml(koreanOptionLabel(option))} | ${rest.map(escapeHtml).join(" | ")}`;
 }).join("<br>");
 }

 function orderCard(order) {
 const cancelled = order.statusKey === "CANCELLED";
 const customerMessage = String(order.customerMessage || "").trim();
 return `<article class="tracking-order">
 <div class="order-head">
 <div>
 <small>注文番号</small>
 <div class="order-code">
 <strong>${escapeHtml(order.orderId)}</strong>
 <button class="copy-code" type="button" data-copy-order="${escapeHtml(order.orderId)}">コピー</button>
 </div>
 </div>
 <span class="status-badge ${cancelled ? "cancelled" : ""}">${escapeHtml(order.status || statusLabels[order.statusKey] || "-")}</span>
 </div>
 <div class="order-meta">
 <div><span>注文日時</span><strong>${escapeHtml(order.placedAt || "-")}</strong></div>
 <div><span>注文数量</span><strong>${Number(order.totalQuantity || 0)}</strong></div>
 <div><span>注文金額</span><strong>${formatPrice(order.totalPrice)}</strong></div>
 </div>
 <p class="order-summary">${formatSummary(order.summary)}</p>
 <div class="order-notice"><strong>現在の進行状況</strong><p>${escapeHtml(order.defaultMessage || "注文の進行状況を確認しています。")}</p></div>
 ${customerMessage ? `<div class="customer-notice"><strong>TEAMSPIRIT-jpからのお知らせ</strong><p>${escapeHtml(customerMessage)}</p></div>` : ""}
 ${statusSteps(order.statusKey)}
 </article>`;
 }

 async function copyText(value, button) {
 try {
 await navigator.clipboard.writeText(value);
 } catch (_error) {
 const temporary = document.createElement("textarea");
 temporary.value = value;
 document.body.appendChild(temporary);
 temporary.select();
 document.execCommand("copy");
 temporary.remove();
 }
 const original = button.textContent;
 button.textContent = "コピー済み";
 setTimeout(() => { button.textContent = original; }, 1400);
 }

 async function submitLookup() {
 const parameters = lookupParameters(input.value);
 if (!parameters.orderId && !parameters.phone) {
 displayError(new Error("注文番号または電話番号を入力してください。"));
 return;
 }

 message.className = "tracking-message loading";
 message.textContent = "注文情報を確認しています…";
 results.innerHTML = "";
 form.querySelector("button").disabled = true;
 try {
 const data = await jsonpRequest(parameters);
 if (!data || data.ok !== true) throw new Error(data?.error || "注文を照会できませんでした。");
 if (!Array.isArray(data.orders) || !data.orders.length) {
 message.className = "tracking-message";
 message.textContent = "一致する注文が見つかりません。入力内容をご確認ください。";
 return;
 }
 message.className = "tracking-message";
 message.textContent = `${data.orders.length}件の注文が見つかりました。`;
 results.innerHTML = data.orders.map(orderCard).join("");
 const url = new URL(location.href);
 url.search = "";
 if (parameters.orderId) url.searchParams.set("orderId", parameters.orderId);
 history.replaceState({}, "", url);
 } catch (error) {
 displayError(error);
 } finally {
 form.querySelector("button").disabled = false;
 }
 }

 form.addEventListener("submit", event => {
 event.preventDefault();
 submitLookup();
 });
 results.addEventListener("click", event => {
 const button = event.target.closest("[data-copy-order]");
 if (button) copyText(button.dataset.copyOrder, button);
 });

 const initialOrderId = new URLSearchParams(location.search).get("orderId");
 if (initialOrderId) {
 input.value = initialOrderId;
 submitLookup();
 }
})();
