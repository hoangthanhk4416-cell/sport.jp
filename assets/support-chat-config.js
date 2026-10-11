window.TEAMSPIRIT_SUPPORT_CONFIG = Object.assign({
  aiEndpoint: "https://script.google.com/macros/s/AKfycbwXQR3Tqy2gtsxINHZ36WZvXsBiVRTWpQoP9tzgFe_p3dR-S01dk-8SEZKd9n9t0zcSGg/exec",
  aiEnabled: true,
  maxAiRequestsPerDay: 10,
  lineUrl: "https://lin.ee/qE1TJJ5",
  instagramUrl: "https://www.instagram.com/teamspirit.jp/"
}, window.TEAMSPIRIT_SUPPORT_CONFIG || {});

(function () {
  function initTeamSpirit2K() {
    if (window.TeamSpiritBackground && !window.__teamSpiritBgInstance) {
      window.__teamSpiritBgInstance = new window.TeamSpiritBackground({
        zIndex: 0,
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
    s.src = "/assets/teamspirit-background.js?v=3.2.0";
    s.defer = true;
    s.onload = initTeamSpirit2K;
    document.head.appendChild(s);
  } else {
    window.addEventListener("DOMContentLoaded", initTeamSpirit2K);
    window.addEventListener("load", initTeamSpirit2K);
  }
})();