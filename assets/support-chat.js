(() => {
  "use strict";
  const cfg = Object.assign({ aiEndpoint: "", aiEnabled: false, maxAiRequestsPerDay: 10, lineUrl: "https://lin.ee/qE1TJJ5", instagramUrl: "https://www.instagram.com/teamspirit.jp/" }, window.TEAMSPIRIT_SUPPORT_CONFIG || {});
  const HISTORY_KEY = "ts-support-history-v2";
  const questions = [
    ["price", "商品の価格を教えてください"], ["size", "サイズの選び方を教えてください"],
    ["order", "注文方法を教えてください"], ["sample", "無料サンプルを申し込みたい"],
    ["delivery", "製作・配送には何日かかりますか？"], ["custom", "ロゴ・背番号・カラーは変更できますか？"],
    ["tracking", "注文・配送状況を確認したい"], ["contact", "担当者に相談したい"]
  ];
  const answers = {
    price: "商品価格は各商品ページに ¥ で表示しています。現在、多くのユニフォームは1枚 ¥4,500です。枚数を入力すると合計金額を計算できます。例：「45枚はいくら？」",
    size: "上着は90(S)〜120(4XL)を目安にお選びいただけます。商品ページの画像2と下部のサイズ表で、着丈・身幅・肩幅・袖丈・身長・体重の目安をご確認ください。",
    order: "商品ページまたは商品一覧の「注文・無料サンプル」ボタンから、サイズ、カラー、数量、背番号、マーキング名、ご要望、配送情報を入力してご注文いただけます。詳しいご相談は、下のLINEからお気軽にお問い合わせください。",
    sample: "商品ページまたは商品一覧の「注文・無料サンプル」ボタンからお申し込みいただけます。担当者がサンプル条件と製作内容を確認します。詳しいご相談は、下のLINEからお気軽にお問い合わせください。",
    delivery: "デザインと注文内容の確定後、製作・処理・配送の目安は約3〜9日です。確定日程は担当者からご案内します。",
    custom: "はい。チームロゴ、カラー、背番号、選手名、フォントなどを変更でき、ご希望に合わせたオリジナルデザインも承ります。高品質な生地を幅広くご用意し、先進的なプリント技術で製作します。「注文・無料サンプル」ボタン、または下のLINEからお気軽にご相談ください。",
    tracking: "注文番号（例：TS-20260815-ABC123）または注文時の電話番号を入力してください。この画面でGoogle Sheetsの最新状況を確認します。",
    contact: "担当者への個別相談は、下のLINEまたはInstagramをご利用ください。"
  };
  const esc = value => String(value || "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  function questionLanguage(value) {
    const text=String(value||"").normalize("NFKC");
    if (/[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(text) || /\b(?:bao nhiêu|đặt hàng|mẫu|còn hàng|chất liệu|tư vấn|số điện thoại)\b/i.test(text)) return "vi";
    if (/\b(?:how|what|price|order|sample|fabric|stock|available|shipping)\b/i.test(text)) return "en";
    return "ja";
  }
  const loadHistory = () => { try { const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); return Array.isArray(value) ? value.slice(-30) : []; } catch (_) { return []; } };
  let history = loadHistory();

  function currentUnitPrice() {
    const visible = document.querySelector(".current-price,.big-price,.product-info .price")?.textContent || "";
    const digits = visible.replace(/[^\d]/g, "");
    return digits ? Number(digits) : 4500;
  }
  function quantityFrom(question) {
    const text = String(question || "").normalize("NFKC");
    const patterns = [/(\d{1,4})\s*(?:枚|着|個|点|セット)/, /(\d{1,4})\s*(?:áo|ao|cái|cai|bộ|bo)\b/i, /(?:数量|số lượng|so luong)\s*[:：]?\s*(\d{1,4})/i];
    for (const pattern of patterns) { const match = text.match(pattern); if (match) return Number(match[1]); }
    if (/(?:いくら|価格|値段|合計|bao nhiêu|bao nhieu|giá|gia)/i.test(text)) { const match = text.match(/\b(\d{1,4})\b/); if (match) return Number(match[1]); }
    return 0;
  }
  function priceAnswer(question) {
    const quantity = quantityFrom(question); if (!quantity) return "";
    const unit = currentUnitPrice(), total = unit * quantity, format = value => new Intl.NumberFormat("ja-JP").format(value);
    const lang=questionLanguage(question);
    if(lang==="vi") return `${quantity} áo × ¥${format(unit)} = ¥${format(total)}.\nĐây là giá sản phẩm tạm tính theo đơn giá hiển thị. Giá cuối cùng, nội dung thiết kế và phí giao hàng sẽ được nhân viên xác nhận trước khi sản xuất. Bạn có thể bấm “Đặt hàng/Mẫu thử miễn phí” hoặc liên hệ LINE để được tư vấn chi tiết nhé.`;
    if(lang==="en") return `${quantity} items × ¥${format(unit)} = ¥${format(total)}.\nThis is an estimate based on the displayed unit price. Staff will confirm customization, shipping and the final total before production. Please use the Order/Free Sample button or contact us on LINE for details.`;
    return `${quantity}枚 × ¥${format(unit)} = ¥${format(total)}です。\nこれは表示単価による商品代の概算です。カスタム内容・送料などを含む最終金額は、製作前に担当者が確認します。`;
  }
  function guidedSalesAnswer(question) {
    const text = String(question || "").normalize("NFKC");
    const lang=questionLanguage(text);
    if (/^(?:xin chào|chào|hello|hi|hey|こんにちは|こんばんは|おはよう)(?:[!！,.。\s]|$)/i.test(text)) {
      if(lang==="vi") return "Xin chào! TEAMSPIRIT-JP rất vui được hỗ trợ bạn. Bạn muốn tìm mẫu sản phẩm, xem giá, chọn kích cỡ, đặt hàng hay yêu cầu thiết kế riêng? Bạn cũng có thể bấm nút “Đặt hàng/Mẫu thử miễn phí” hoặc liên hệ LINE để được tư vấn chi tiết nhé.";
      if(lang==="en") return "Hello! Welcome to TEAMSPIRIT-JP. How can we help you with product models, prices, sizing, ordering or a custom design? You can also use the Order/Free Sample button or contact us on LINE for detailed advice.";
      return "こんにちは！TEAMSPIRIT-JPへようこそ。商品モデル、価格、サイズ、注文方法、オリジナルデザインについてお気軽にご質問ください。「注文・無料サンプル」ボタン、またはLINEからも詳しくご相談いただけます。";
    }
    if (/(?:在庫|在庫あり|在庫切れ|品切れ|売り切れ|(?:商品|製品|TEAMSPIRIT-[A-Z0-9-]+).*(?:ある|あります|ございます|扱い)|モデル|デザイン|mẫu|mau|còn hàng|con hang|hết hàng|het hang)/i.test(text)) {
      if(lang==="vi") return "Website hiện vẫn có đầy đủ nhiều mẫu sản phẩm để bạn lựa chọn. Ngoài các mẫu đang hiển thị, chúng tôi còn nhận thiết kế riêng theo yêu cầu, có nhiều loại vải cao cấp và sử dụng công nghệ in tiên tiến. Bạn có thể bấm nút “Đặt hàng/Mẫu thử miễn phí” hoặc liên hệ LINE để được tư vấn chi tiết nhé.";
      if(lang==="en") return "The website currently offers a wide selection of product models. You can also request a custom design made with high-quality fabrics and advanced printing technology. Please use the Order/Free Sample button or contact us on LINE for detailed advice.";
      return "ウェブサイトには現在も豊富な商品モデルをご用意しています。掲載モデルから選べるほか、ご希望に合わせたオリジナルデザインも承ります。高品質な生地を幅広く取り揃え、先進的なプリント技術で製作します。「注文・無料サンプル」ボタン、または下のLINEからお気軽にご相談ください。";
    }
    if (/(?:注文方法|注文したい|購入したい|申し込み|申込み|無料サンプル|発注|đặt hàng|dat hang|đăng ký|dang ky|mua hàng|mua hang)/i.test(text)) {
      if(lang==="vi") return "Bạn có thể bấm nút “Đặt hàng/Mẫu thử miễn phí” trên trang sản phẩm hoặc danh sách sản phẩm, sau đó nhập kích cỡ, màu sắc, số lượng, số áo, tên in và thông tin giao hàng. Nếu cần hỗ trợ chi tiết, hãy liên hệ với chúng tôi qua LINE nhé.";
      if(lang==="en") return "Use the Order/Free Sample button on a product page or product list, then enter the size, color, quantity, number, printed name and delivery information. Please contact us on LINE if you need detailed assistance.";
      return answers.order;
    }
    if (/(?:生地|素材|布|プリント|印刷|昇華|刺繍|fabric|vải|vai|chất liệu|chat lieu|in ấn|in an)/i.test(text)) {
      if(lang==="vi") return "Chúng tôi có nhiều loại vải cao cấp phù hợp với từng mục đích sử dụng và có thể in logo, số áo, chữ, màu sắc bằng công nghệ in tiên tiến. Bạn hãy bấm “Đặt hàng/Mẫu thử miễn phí” để gửi yêu cầu hoặc liên hệ LINE để được tư vấn chi tiết nhé.";
      if(lang==="en") return "We offer a range of high-quality fabrics and can produce logos, numbers, lettering and colors using advanced printing technology. Send your request through the Order/Free Sample button or contact us on LINE for details.";
      return "用途やご希望に合わせて、高品質な生地を幅広くご用意しています。ロゴ・番号・文字・カラーは、先進的なプリント技術を使って製作できます。「注文・無料サンプル」ボタンからご要望を送るか、下のLINEから詳しくご相談ください。";
    }
    return "";
  }
  function lookupParameters(question) {
    const order = String(question || "").toUpperCase().match(/TS-\d{8}-[A-Z0-9]{1,10}/)?.[0];
    if (order) return { orderId: order };
    const trackingIntent = /注文|配送|状況|追跡|伝票|電話|運送|order|tracking|mã|ma don|vận đơn|van don|số điện thoại|so dien thoai/i.test(question);
    let phone = String(question || "").replace(/\D/g, "");
    if (/^82\d{9,10}$/.test(phone)) phone = `0${phone.slice(2)}`;
    if (!phone.startsWith("0") && /^\d{9,10}$/.test(phone)) phone = `0${phone}`;
    return trackingIntent && /^0\d{8,10}$/.test(phone) ? { phone } : {};
  }
  function trackingRequest(parameters) {
    return new Promise((resolve, reject) => {
      if (!/^https:\/\/script\.google\.com\//.test(cfg.aiEndpoint)) return reject(new Error("注文照会サービスは接続されていません。"));
      const callback = `__tsSupportLookup_${Date.now()}_${Math.random().toString(36).slice(2)}`, script = document.createElement("script"), url = new URL(cfg.aiEndpoint);
      url.searchParams.set("mode", "lookup"); url.searchParams.set("callback", callback); Object.entries(parameters).forEach(([key,value]) => url.searchParams.set(key,value));
      const cleanup = () => { delete window[callback]; script.remove(); clearTimeout(timer); };
      const timer = setTimeout(() => { cleanup(); reject(new Error("注文照会がタイムアウトしました。")); }, 15000);
      window[callback] = data => { cleanup(); resolve(data); }; script.onerror = () => { cleanup(); reject(new Error("注文照会サービスに接続できません。")); };
      script.src = url.toString(); document.head.appendChild(script);
    });
  }
  function trackingAnswer(data) {
    if (!data?.ok) throw new Error(data?.error || "注文を照会できませんでした。");
    if (!Array.isArray(data.orders) || !data.orders.length) return "一致する注文が見つかりません。注文番号または電話番号をご確認ください。";
    const statuses={NEW:"受付済み",CONFIRMED:"注文確認",DESIGNING:"デザイン作業中",PRODUCTION:"制作中",SHIPPING:"配送中",COMPLETED:"完了",CANCELLED:"キャンセル"};
    const summary=value=>String(value||"-").replace(/기존 디자인 유지/g,"既存デザインのまま").replace(/컬러 변경/g,"カラー変更を希望");
    return data.orders.slice(0,3).map(order => {
      const total = new Intl.NumberFormat("ja-JP").format(Number(order.totalPrice || 0));
      return `注文番号：${order.orderId}\n状況：${statuses[order.statusKey] || order.status || "確認中"}\n注文日時：${order.placedAt || "-"}\n数量：${Number(order.totalQuantity || 0)}\n金額：¥${total}\n商品：${summary(order.summary)}${order.customerMessage ? `\nお知らせ：${order.customerMessage}` : ""}`;
    }).join("\n\n");
  }

  function mount() {
    if (document.getElementById("tsSupportLauncher")) return;
    document.body.insertAdjacentHTML("beforeend", `<button id="tsSupportLauncher" class="ts-support-launcher" type="button" aria-label="サポートを開く" aria-expanded="false" aria-controls="tsSupportPanel"><img src="/assets/support-launcher-v1.png" width="1983" height="793" alt="" aria-hidden="true" decoding="async"></button><section id="tsSupportPanel" class="ts-support-panel" role="dialog" aria-modal="false" aria-labelledby="tsSupportTitle" hidden><header class="ts-support-head"><strong id="tsSupportTitle">TEAMSPIRIT-JP サポート</strong><button class="ts-support-reset" type="button">履歴を消去</button><button class="ts-support-close" type="button" aria-label="閉じる">×</button></header><div class="ts-support-body"><p class="ts-support-intro">ご質問を選択するか、下に入力してください。</p><div class="ts-support-questions">${questions.map(([key,label]) => `<button class="ts-support-question" type="button" data-support-question="${key}">${label}</button>`).join("")}</div><div id="tsSupportMessages" class="ts-support-messages" role="log" aria-live="polite"></div><div class="ts-support-controls"><p class="ts-support-api-note">その他のご質問・注文照会</p><form id="tsSupportForm" class="ts-support-form"><input id="tsSupportInput" class="ts-support-input" maxlength="500" placeholder="質問・注文番号・電話番号" aria-label="その他の質問"><button class="ts-support-send" type="submit">送信</button></form><div class="ts-support-links"><a class="ts-support-line notranslate" translate="no" href="${esc(cfg.lineUrl)}" target="_blank" rel="noopener">LINE</a><a class="ts-support-instagram notranslate" translate="no" href="${esc(cfg.instagramUrl)}" target="_blank" rel="noopener">Instagram</a></div></div></div></section>`);
    const launcher=document.getElementById("tsSupportLauncher"), panel=document.getElementById("tsSupportPanel"), messages=document.getElementById("tsSupportMessages"), form=document.getElementById("tsSupportForm"), input=document.getElementById("tsSupportInput"), send=form.querySelector("button");
    function render() { messages.innerHTML=history.map(item=>`<div class="ts-support-message ${item.role}"><small>${item.role === "user" ? "お客様" : "サポート"}</small><p>${esc(item.text)}</p></div>`).join(""); messages.scrollTop=messages.scrollHeight; }
    function add(role,text) { history.push({role,text:String(text),at:Date.now()}); history=history.slice(-30); localStorage.setItem(HISTORY_KEY,JSON.stringify(history)); render(); }
    function toggle(force){const open=typeof force==="boolean"?force:panel.hidden;panel.hidden=!open;launcher.setAttribute("aria-expanded",String(open));if(open){render();input.focus();}}
    render(); launcher.addEventListener("click",()=>toggle()); panel.querySelector(".ts-support-close").addEventListener("click",()=>toggle(false));
    panel.querySelector(".ts-support-reset").addEventListener("click",()=>{history=[];localStorage.removeItem(HISTORY_KEY);render();add("assistant","会話履歴を削除しました。新しいご質問をどうぞ。");});
    panel.addEventListener("click",event=>{const button=event.target.closest("[data-support-question]");if(!button)return;const key=button.dataset.supportQuestion,label=questions.find(item=>item[0]===key)?.[1]||"";add("user",label);add("assistant",answers[key]);if(key==="tracking")input.focus();});
    document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!panel.hidden)toggle(false);});
    form.addEventListener("submit",async event=>{
      event.preventDefault();const question=input.value.trim();if(!question)return;input.value="";add("user",question);send.disabled=true;
      try {
        const calculated=priceAnswer(question); if(calculated){add("assistant",calculated);return;}
        const lookup=lookupParameters(question); if(lookup.orderId||lookup.phone){add("assistant","注文情報を確認しています…");const data=await trackingRequest(lookup);history.pop();add("assistant",trackingAnswer(data));return;}
        if (/(?:注文|配送).*(?:状況|確認|追跡)|追跡|伝票|運送状況|mã đơn|ma don|van don|vận đơn|số điện thoại|so dien thoai/i.test(question) && !lookup.orderId && !lookup.phone){add("assistant",answers.tracking);return;}
        const guided=guidedSalesAnswer(question); if(guided){add("assistant",guided);return;}
        if(!cfg.aiEnabled||!cfg.aiEndpoint){add("assistant","AI相談は現在利用できません。LINEまたはInstagramからお問い合わせください。");return;}
        const day=new Date().toISOString().slice(0,10),key=`ts-support-ai-${day}`,used=Number(localStorage.getItem(key)||0);if(used>=Number(cfg.maxAiRequestsPerDay||10)){add("assistant","本日のAI相談回数に達しました。LINEまたはInstagramからお問い合わせください。");return;}
        add("assistant","回答を作成しています…");
        const recent=history.filter(item=>item.text!=="回答を作成しています…").slice(-9,-1).map(item=>({role:item.role,content:item.text.slice(0,600)}));
        const contextText=recent.slice(-4).map(item=>`${item.role==="assistant"?"サポート":"お客様"}: ${item.content}`).join("\n");
        const contextualQuestion=`${contextText?`直前の会話:\n${contextText}\n`:""}現在の質問: ${question}`.slice(-500);
        const response=await fetch(cfg.aiEndpoint,{method:"POST",headers:{"Content-Type":"text/plain;charset=utf-8"},body:JSON.stringify({action:"support_chat",question:contextualQuestion,history:recent,context:{title:document.title,url:location.href,productId:location.pathname.match(/\/products\/([^/]+)/)?.[1]||"",unitPrice:currentUnitPrice()}})});
        const data=await response.json();history.pop();if(!response.ok||!data.ok||!data.answer)throw new Error(data.error||"AI response error");localStorage.setItem(key,String(used+1));add("assistant",data.answer);
      } catch(_){if(history.at(-1)?.text==="回答を作成しています…"||history.at(-1)?.text==="注文情報を確認しています…")history.pop();add("assistant","接続できませんでした。入力内容をご確認いただくか、LINEまたはInstagramからお問い合わせください。");}
      finally{send.disabled=false;input.focus();}
    });
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount);else mount();
})();
