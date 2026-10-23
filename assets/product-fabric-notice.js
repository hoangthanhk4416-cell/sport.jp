(()=>{
  const message = "生地は2種類ございます。表示価格は通常生地です。高級ジャカード生地は＋500円でお選びいただけます。";
  const style = document.createElement("style");
  style.textContent = "#ts-fabric-notice{position:fixed;right:18px;bottom:18px;z-index:9999;width:min(360px,calc(100vw - 32px));padding:16px 42px 16px 16px;background:#fff;color:#111;border:1px solid rgba(17,17,17,.14);border-radius:12px;box-shadow:0 14px 40px rgba(0,0,0,.2);font-family:inherit;opacity:0;transform:translateY(10px);transition:opacity .2s ease,transform .2s ease}#ts-fabric-notice.is-visible{opacity:1;transform:translateY(0)}#ts-fabric-notice strong{display:block;margin-bottom:6px;font-size:14px}#ts-fabric-notice p{margin:0;font-size:13px;line-height:1.65}#ts-fabric-notice button{position:absolute;top:7px;right:8px;width:28px;height:28px;border:0;border-radius:50%;background:#f1f1f1;color:#333;font-size:20px;line-height:1;cursor:pointer}#ts-fabric-notice button:hover{background:#e5e5e5}@media(max-width:600px){#ts-fabric-notice{right:12px;bottom:12px;width:calc(100vw - 24px);padding:15px 42px 15px 15px}}";
  document.head.appendChild(style);
  const show = () => {
    if (document.getElementById("ts-fabric-notice")) return;
    const notice = document.createElement("aside");
    notice.id = "ts-fabric-notice";
    notice.setAttribute("role", "status");
    notice.innerHTML = "<button type=\"button\" aria-label=\"閉じる\">×</button><strong>生地について</strong><p>" + message + "</p>";
    document.body.appendChild(notice);
    requestAnimationFrame(() => notice.classList.add("is-visible"));
    notice.querySelector("button").addEventListener("click", () => {
      notice.classList.remove("is-visible");
      setTimeout(() => notice.remove(), 220);
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", show, {once:true});
  else show();
})();
