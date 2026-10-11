window.TEAMSPIRIT_SUPPORT_CONFIG = Object.assign({
  aiEndpoint: "https://script.google.com/macros/s/AKfycbwXQR3Tqy2gtsxINHZ36WZvXsBiVRTWpQoP9tzgFe_p3dR-S01dk-8SEZKd9n9t0zcSGg/exec",
  aiEnabled: true,
  maxAiRequestsPerDay: 10,
  lineUrl: "https://lin.ee/qE1TJJ5",
  instagramUrl: "https://www.instagram.com/teamspirit.jp/"
}, window.TEAMSPIRIT_SUPPORT_CONFIG || {});

(function () {
  if (!document.getElementById("teamspirit-bg-subpage-fix")) {
    var st = document.createElement("style");
    st.id = "teamspirit-bg-subpage-fix";
    st.textContent = [
      "html, body { background: transparent !important; background-color: transparent !important; }",
      "#teamspirit-bg-root { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; z-index: -1 !important; pointer-events: none !important; }",
      "#app, main, header:not(.full-head):not(.head), footer, .notice, .page-head, .article-page, .guide-page, .order-guide, .faq-page, .tracking-main, .login-page, .placeholder, .full-footer { position: relative; z-index: 2; }",
      ".full-head, .head { position: sticky !important; top: 0 !important; z-index: 30 !important; }",
      ".article-page, .login-page, .placeholder, .tracking-main { background: transparent !important; }",
      ".article-page > .article, main.guide-page, main.order-guide, main.faq-page, .login-page > .login-panel, .placeholder > .card { position: relative; z-index: 2; background: rgba(255, 255, 255, 0.96) !important; color: #111111 !important; border-radius: 18px !important; padding: 36px 28px !important; box-shadow: 0 20px 55px rgba(0, 0, 0, 0.45) !important; border: 1px solid rgba(255, 255, 255, 0.4) !important; }",
      "main.guide-page, main.order-guide, main.faq-page { margin: 36px auto 72px !important; width: min(1120px, calc(100% - 32px)) !important; }"
    ].join("\n");
    document.head.appendChild(st);
  }

  function initTeamSpirit2K() {
    if (window.TeamSpiritBackground && !window.__teamSpiritBgInstance) {
      window.__teamSpiritBgInstance = new window.TeamSpiritBackground({
        zIndex: -1,
        darkenAmount: 0.42,
        veilOpacity: 0.42,
        scrollSensitivity: 1.0
      });
    }
  }
  if (window.TeamSpiritBackground) {
    initTeamSpirit2K();
  } else if (!document.querySelector('script[src*="teamspirit-background.js"]')) {
    var s = document.createElement("script");
    s.src = "/assets/teamspirit-background.js?v=3.2.1";
    s.defer = true;
    s.onload = initTeamSpirit2K;
    document.head.appendChild(s);
  } else {
    window.addEventListener("DOMContentLoaded", initTeamSpirit2K);
    window.addEventListener("load", initTeamSpirit2K);
  }
})();