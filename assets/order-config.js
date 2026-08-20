window.TEAMSPIRIT_ORDER_CONFIG = {
  endpoint: "https://script.google.com/macros/s/AKfycbwXQR3Tqy2gtsxINHZ36WZvXsBiVRTWpQoP9tzgFe_p3dR-S01dk-8SEZKd9n9t0zcSGg/exec",
  spreadsheetId: "1AtQo4vi6nlYV3yzRPUit0iiJTmvgllGplSSfgl1aigU",
  spreadsheetUrl: "https://docs.google.com/spreadsheets/d/1AtQo4vi6nlYV3yzRPUit0iiJTmvgllGplSSfgl1aigU/edit",
};

/* Restore TEAMSPIRIT support chat on pages that load order-config.js. */
(() => {
  if (!document.getElementById("teamspirit-support-chat-style")) {
    const style = document.createElement("link");
    style.id = "teamspirit-support-chat-style";
    style.rel = "stylesheet";
    style.href = "/assets/support-chat.css?v=20260820-1";
    document.head.appendChild(style);
  }

  const loadChat = () => {
    if (document.getElementById("teamspirit-support-chat-script")) return;
    const chat = document.createElement("script");
    chat.id = "teamspirit-support-chat-script";
    chat.src = "/assets/support-chat.js?v=20260820-1";
    chat.async = false;
    document.body.appendChild(chat);
  };

  if (window.TEAMSPIRIT_SUPPORT_CHAT_CONFIG) {
    loadChat();
    return;
  }

  if (!document.getElementById("teamspirit-support-chat-config")) {
    const config = document.createElement("script");
    config.id = "teamspirit-support-chat-config";
    config.src = "/assets/support-chat-config.js?v=20260820-1";
    config.async = false;
    config.onload = loadChat;
    document.body.appendChild(config);
  }
})();
