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
