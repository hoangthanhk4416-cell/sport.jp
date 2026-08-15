const fs = require("fs");
const vm = require("vm");
const assert = require("assert");

const properties = new Map([["CHATANYWHERE_API_KEY", "test-key"], ["CHATANYWHERE_MODEL", "gpt-4o-mini"]]);
let capturedRequest;
const context = {
  console,
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: key => properties.get(key) || null, setProperty: (key, value) => properties.set(key, value) }) },
  Session: { getScriptTimeZone: () => "Asia/Tokyo" },
  Utilities: { formatDate: () => "2026-08-15" },
  UrlFetchApp: { fetch: (url, options) => { capturedRequest = { url, options }; return { getResponseCode: () => 200, getContentText: () => JSON.stringify({ choices: [{ message: { content: "承知しました。担当者が確認します。" } }] }) }; } },
  ContentService: { MimeType: { JSON: "json" }, createTextOutput: text => ({ text, setMimeType() { return this; } }) }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require("path").join(__dirname, "..", "integrations", "google-apps-script-support-chat", "Code.gs"), "utf8"), context);
const response = context.doPost({ postData: { contents: JSON.stringify({ action: "support_chat", question: "特別な注文について相談できますか？", context: { title: "商品", url: "https://teamspiritsport.jp/products/teamspirit-jp04/" } }) } });
const payload = JSON.parse(response.text);
assert.equal(payload.ok, true);
assert.match(payload.answer, /担当者/);
assert.equal(capturedRequest.url, "https://api.chatanywhere.org/v1/chat/completions");
assert.equal(capturedRequest.options.headers.Authorization, "Bearer test-key");
assert.equal(JSON.parse(capturedRequest.options.payload).model, "gpt-4o-mini");
assert.equal(properties.get("SUPPORT_CHAT_COUNT_2026-08-15"), "1");
console.log("support-chat-gas.test.js: PASS");
