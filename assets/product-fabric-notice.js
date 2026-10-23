(()=>{
  const message = "生地は2種類です。表示価格は通常生地で、高級ジャカードは＋500円です。";
  const style = document.createElement("style");
  style.textContent = `#ts-fabric-notice{position:fixed;left:50%;top:50%;right:auto;bottom:auto;z-index:9999;width:min(420px,calc(100vw - 32px));padding:12px 44px 12px 16px;background:rgba(15,23,42,.86);color:#fff;border:1px solid rgba(255,255,255,.28);border-radius:14px;box-shadow:0 16px 44px rgba(0,0,0,.3);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);font-family:inherit;text-align:center;opacity:0;transform:translate(-50%,-50%) scale(.98);transition:opacity .2s ease,transform .2s ease}#ts-fabric-notice.is-visible{opacity:1;transform:translate(-50%,-50%) scale(1)}#ts-fabric-notice strong{display:inline;font-size:13px;font-weight:800;margin-right:8px}#ts-fabric-notice .ts-fabric-message{font-size:13px;line-height:1.5}#ts-fabric-notice button{position:absolute;top:6px;right:8px;width:28px;height:28px;border:1px solid rgba(255,255,255,.18);border-radius:50%;background:rgba(255,255,255,.16);color:#fff;font-size:19px;line-height:1;cursor:pointer}#ts-fabric-notice button:hover{background:rgba(255,255,255,.28)}@media(max-width:600px){#ts-fabric-notice{width:calc(100vw - 32px);padding:11px 42px 11px 14px}#ts-fabric-notice strong,#ts-fabric-notice .ts-fabric-message{font-size:12px}}`;
  document.head.appendChild(style);
  const show = () => {
    if (document.getElementById("ts-fabric-notice")) return;
    const notice = document.createElement("aside");
    notice.id = "ts-fabric-notice";
    notice.setAttribute("role", "status");
    notice.innerHTML = "<button type=\"button\" aria-label=\"閉じる\">×</button><strong>生地について</strong><span class=\"ts-fabric-message\">" + message + "</span>";
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