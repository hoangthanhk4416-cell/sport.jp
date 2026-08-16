# TEAMSPIRIT-JP support chat Web App

This is a separate Apps Script project so the existing order-to-Google-Sheets `doPost` remains unchanged.

1. Create a new standalone Google Apps Script project and paste `Code.gs`.
2. In **Project Settings > Script Properties**, add `CHATANYWHERE_API_KEY`. Optionally add `CHATANYWHERE_MODEL` (default: `gpt-4o-mini`).
3. Deploy as **Web app**, execute as the owner, access **Anyone**.
4. Copy the `/exec` URL to `/assets/support-chat-config.js`, set `aiEndpoint` to that URL and `aiEnabled` to `true`.
5. Do not put the API key in website files, GitHub, or the Editor.

Preset FAQ replies are local and do not call this Web App. Only free-form questions use an API request. The browser is capped at 10 requests/day and the Apps Script project has a global safety cap of 100 requests/day.
