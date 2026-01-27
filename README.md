# LINE Echo Bot

這是一個使用 FastAPI 和 `line-bot-sdk` 建立的簡單 LINE Echo Bot。由 `uv` 管理。

## 安裝

1. 確保已安裝 Python 和 `uv`。
2. 安裝依賴：
   ```bash
   uv sync
   ```

## 設定

1. 在 LINE Developers Console 建立一個 Messaging API Channel。
2. 複製 `.env.example` 為 `.env`：
   ```bash
   cp .env.example .env
   # 或在 Windows 上手動複製
   ```
3. 將你的 Channel Access Token 和 Channel Secret 填入 `.env` 檔案中。

## 執行

執行以下指令啟動伺服器：

```bash
uv run uvicorn main:app --reload
```

## 測試 (使用 ngrok)

由於 LINE Platform 需要 HTTPS callback URL，你需要使用 ngrok 將本地伺服器公開。

1. 安裝 ngrok。
2. 執行 ngrok：
   ```bash
   ngrok http 8000
   ```
3. 複製 ngrok 產生的 https URL (例如 `https://xxxx.ngrok-free.app`)。
4. 在 LINE Developers Console 的 Messaging API 設定中，設定 Webhook URL 為：
   `https://xxxx.ngrok-free.app/callback`
5. 開啟 "Use webhook"。
6. 加入你的 Bot 為好友並傳送訊息，它應該會回覆相同的訊息。
