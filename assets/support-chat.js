(() => {
  "use strict";
  const cfg = Object.assign({ aiEndpoint: "", aiEnabled: false, maxAiRequestsPerDay: 10, lineUrl: "https://lin.ee/qE1TJJ5", instagramUrl: "https://www.instagram.com/teamspirit.jp/" }, window.TEAMSPIRIT_SUPPORT_CONFIG || {});
  const questions = [
    ["price", "商品の価格を教えてください"],
    ["size", "サイズの選び方を教えてください"],
    ["order", "注文方法を教えてください"],
    ["sample", "無料サンプルを申し込みたい"],
    ["delivery", "製作・配送には何日かかりますか？"],
    ["custom", "ロゴ・背番号・カラーは変更できますか？"],
    ["contact", "担当者に相談したい"]
  ];
  const answers = {
    price: "商品価格は各商品ページに ¥ で表示しています。現在、多くのユニフォームは ¥4,500 です。数量やカスタム内容によって最終金額が変わる場合があるため、製作前に担当者が確認します。",
    size: "上着は 90(S)〜120(4XL) を目安にお選びいただけます。商品ページの画像2と下部のサイズ表で、着丈・身幅・肩幅・袖丈・身長・体重の目安をご確認ください。ゆったり着たい場合は1サイズ上がおすすめです。",
    order: "商品を選び、商品ページの「注文・無料サンプル」を押してください。サイズ、カラー、数量、背番号、マーキング名、ご要望を入力し、次に配送情報を入力すると注文を送信できます。",
    sample: "商品ページまたは商品一覧の「注文・無料サンプル」からお申し込みください。商品・サイズ・ご要望を入力後、担当者がサンプル条件と製作内容を確認してご連絡します。",
    delivery: "デザインと注文内容の確定後、製作・処理・配送の目安は約3〜9日です。数量やカスタム内容、配送先により変わるため、確定日程は担当者からご案内します。",
    custom: "はい。チームロゴ、カラー、背番号、選手名、フォントなどを相談できます。ご希望を注文フォームに記入すると、製作前に担当者がデザインと最終金額を確認します。",
    contact: "担当者への個別相談は、下のLINEまたはInstagramをご利用ください。"
  };
  function esc(value) { return String(value || "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function mount() {
    if (document.getElementById("tsSupportLauncher")) return;
    document.body.insertAdjacentHTML("beforeend", `<button id="tsSupportLauncher" class="ts-support-launcher" type="button" aria-label="サポートを開く" aria-expanded="false" aria-controls="tsSupportPanel"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-5 4v-4.5A2.5 2.5 0 0 1 4 13.5z"/><path d="M8 8h8M8 12h5"/></svg></button><section id="tsSupportPanel" class="ts-support-panel" role="dialog" aria-modal="false" aria-labelledby="tsSupportTitle" hidden><header class="ts-support-head"><strong id="tsSupportTitle">TEAMSPIRIT-JP サポート</strong><button class="ts-support-close" type="button" aria-label="閉じる">×</button></header><div class="ts-support-body"><p class="ts-support-intro">ご質問を選択してください。よくある質問はすぐにご案内します。</p><div class="ts-support-questions">${questions.map(([key,label]) => `<button class="ts-support-question" type="button" data-support-question="${key}">${label}</button>`).join("")}</div><div id="tsSupportAnswer" class="ts-support-answer" role="status" aria-live="polite" hidden></div><p class="ts-support-api-note">その他のご質問（AI相談）</p><form id="tsSupportForm" class="ts-support-form"><input id="tsSupportInput" class="ts-support-input" maxlength="500" placeholder="質問を入力" aria-label="その他の質問"><button class="ts-support-send" type="submit">送信</button></form><div class="ts-support-links"><a class="ts-support-line" href="${esc(cfg.lineUrl)}" target="_blank" rel="noopener">LINE</a><a class="ts-support-instagram" href="${esc(cfg.instagramUrl)}" target="_blank" rel="noopener">Instagram</a></div></div></section>`);
    const launcher = document.getElementById("tsSupportLauncher"), panel = document.getElementById("tsSupportPanel"), answer = document.getElementById("tsSupportAnswer"), form = document.getElementById("tsSupportForm"), input = document.getElementById("tsSupportInput"), send = form.querySelector("button");
    function toggle(force) { const open = typeof force === "boolean" ? force : panel.hidden; panel.hidden = !open; launcher.setAttribute("aria-expanded", String(open)); if (open) panel.querySelector(".ts-support-question")?.focus(); }
    function show(text) { answer.textContent = text; answer.hidden = false; answer.scrollIntoView({block:"nearest"}); }
    launcher.addEventListener("click", () => toggle()); panel.querySelector(".ts-support-close").addEventListener("click", () => toggle(false));
    panel.addEventListener("click", event => { const button = event.target.closest("[data-support-question]"); if (button) show(answers[button.dataset.supportQuestion]); });
    document.addEventListener("keydown", event => { if (event.key === "Escape" && !panel.hidden) toggle(false); });
    form.addEventListener("submit", async event => {
      event.preventDefault(); const question = input.value.trim(); if (!question) return;
      if (!cfg.aiEnabled || !cfg.aiEndpoint) { show("AI相談は現在テスト設定中です。よくある質問を選ぶか、LINEまたはInstagramからお問い合わせください。"); return; }
      const day = new Date().toISOString().slice(0,10), key = `ts-support-ai-${day}`, used = Number(localStorage.getItem(key) || 0);
      if (used >= Number(cfg.maxAiRequestsPerDay || 10)) { show("本日のAI相談回数に達しました。LINEまたはInstagramからお問い合わせください。"); return; }
      send.disabled = true; show("回答を作成しています…");
      try {
        const response = await fetch(cfg.aiEndpoint, { method:"POST", headers:{"Content-Type":"text/plain;charset=utf-8"}, body:JSON.stringify({ action:"support_chat", question, context:{ title:document.title, url:location.href, productId:document.body.dataset.productId || "" }}) });
        const data = await response.json(); if (!response.ok || !data.ok || !data.answer) throw new Error(data.error || "AI response error");
        localStorage.setItem(key, String(used + 1)); show(data.answer); input.value = "";
      } catch (_) { show("AI相談に接続できませんでした。LINEまたはInstagramからお問い合わせください。"); }
      finally { send.disabled = false; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
