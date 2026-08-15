# TEAMSPIRIT order intake

This Apps Script receives checkout payloads from the static GitHub Pages website and appends them to the TEAMSPIRIT Google Sheet.

## One-time deployment

1. Open the destination Google Sheet.
2. Select **Extensions → Apps Script**.
3. Replace the editor contents with `Code.gs`.
4. Select **Deploy → New deployment → Web app**.
5. Execute as: **Me**. Who has access: **Anyone**.
6. Authorize the script and copy the `/exec` deployment URL.
7. Paste that URL into `assets/order-config.js` as `endpoint`.

Do not place Google credentials or API keys in the website repository.

## Apply or repair the spreadsheet layout

After pasting a new `Code.gs` version:

1. Select `setupOrderSheets` in the function menu.
2. Click **Run** and approve the requested spreadsheet/trigger permissions.
3. The function repairs headers and dropdowns, normalizes legacy design values, and installs the edit trigger that keeps order status synchronized between `Đơn hàng` and `Chi tiết sản phẩm`.

The same setup also creates `Tra cứu vận đơn`, a Korean-language customer tracking tab. Column `고객 안내 메시지 (직접 입력)` is reserved for staff-written customer notices and is preserved when order status changes. The public lookup page reads only this tracking tab and never exposes the internal Vietnamese management columns.
# AI support chat in the existing order Web App

The same deployed Web App now routes requests by payload:

- `{ "action": "support_chat", ... }` calls ChatAnywhere and returns `{ ok, answer }`.
- Existing order payloads continue through the unchanged Google Sheets order flow.

In **Project Settings > Script Properties**, keep `SHEET_LAYOUT_VERSION` and add:

- `CHATANYWHERE_API_KEY`: the private API key (never place it in website files).
- `CHATANYWHERE_MODEL`: `gpt-4o-mini`.

After replacing `Code.gs`, update the existing Web App deployment with a new version. Do not create a second order endpoint.

## Multilingual store knowledge for the support bot

After installing this version, run `setupBotKnowledgeSheets` once. It creates and seeds three editable tabs:

- `BOT_KNOWLEDGE`: public store facts and policies.
- `PRODUCTS`: public product facts, prices, sizes, fabrics, printing and URLs.
- `BOT_FAQ`: approved answers and matching keywords.

Only rows whose final `Bật` checkbox is selected are eligible for AI context. The script ranks rows against the current question and sends only a small relevant subset to the AI. It never sends `Đơn hàng`, `Chi tiết sản phẩm`, `Tra cứu vận đơn`, customer names, phone numbers or addresses to the AI.

The website also sends the public title, meta description and a limited excerpt from the page currently being viewed. The assistant detects the customer's latest language and answers in that language. Staff can update the three bot tabs without changing website code or redeploying the Web App.
