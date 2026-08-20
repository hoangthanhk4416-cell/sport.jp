(() => {
  "use strict";

  const config = window.TEAMSPIRIT_ORDER_CONFIG || {};
  const lineUrl = config.lineUrl || "https://lin.ee/qE1TJJ5";
  const selector = [
    'a[href*="lin.ee"]',
    'a[href*="line.me"]',
    'a[href*="/pages/line"]',
    '[data-line-inquiry]'
  ].join(",");

  function connectLineLinks(root = document) {
    root.querySelectorAll(selector).forEach(link => {
      if (!(link instanceof HTMLAnchorElement)) return;
      link.href = lineUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.removeAttribute("data-line-inquiry");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => connectLineLinks(), { once: true });
  } else {
    connectLineLinks();
  }
})();
