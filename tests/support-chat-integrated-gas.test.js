const fs = require("fs");
const vm = require("vm");
const path = require("path");
const assert = require("assert");

const properties = new Map([["CHATANYWHERE_API_KEY", "test-key"], ["CHATANYWHERE_MODEL", "gpt-4o-mini"]]);
let aiRequests = 0;
let capturedAiPayload = null;
const context = {
  console,
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: key => properties.get(key) || null, setProperty: (key, value) => properties.set(key, value), deleteProperty: key => properties.delete(key) }) },
  Session: { getScriptTimeZone: () => "Asia/Tokyo" },
  Utilities: { formatDate: () => "2026-08-15" },
  UrlFetchApp: { fetch: (_url, options) => { aiRequests += 1; capturedAiPayload = JSON.parse(options.payload); return { getResponseCode: () => 200, getContentText: () => JSON.stringify({ choices: [{ message: { content: "担当者に確認します。" } }] }) }; } },
  ContentService: { MimeType: { JSON: "json", JAVASCRIPT: "javascript" }, createTextOutput: text => ({ text, setMimeType() { return this; } }) }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "integrations", "google-apps-script", "Code.gs"), "utf8"), context);

const chatResponse = JSON.parse(context.doPost({ postData: { contents: JSON.stringify({ action: "support_chat", question: "大会用の注文について相談できますか？", context: { title: "商品ページ", description: "公開説明", pageExcerpt: "公開されている商品情報" } }) } }).text);
assert.equal(chatResponse.ok, true);
assert.equal(aiRequests, 1);
assert.match(chatResponse.answer, /担当者/);
assert.match(capturedAiPayload.messages[0].content, /multilingual/);
assert.match(capturedAiPayload.messages.at(-1).content, /公開されている商品情報/);
assert.doesNotMatch(capturedAiPayload.messages[0].content, /customer names.*CURATED STORE CONTEXT:[\s\S]*TS-2026/i);

const invalidOrderResponse = JSON.parse(context.doPost({ postData: { contents: "{}" } }).text);
assert.equal(invalidOrderResponse.ok, false);
assert.equal(aiRequests, 1, "order requests must not be routed to the AI API");
console.log("support-chat-integrated-gas.test.js: PASS");
