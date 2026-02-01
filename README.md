# LINE Voice & Text Summarizer Bot

這是一個基於 FastAPI 和 `line-bot-sdk` 建立的 LINE 機器人，支援語音轉文字、自動摘要，並能將結果同步紀錄至 Notion 與 Google Sheets。由 `uv` 管理。

## 功能特點
- **語音轉文字**: 使用 Google Gemini 2.5-flash 精準轉錄語音內容。
- **自動摘要**: 自動產生語音或長文字訊息的繁體中文摘要。
- **雙平台備份**: 自動將結果存入 Notion 資料庫與 Google Sheets 試算表。
- **分類管理**: 自動區分「語音摘要」與「文字摘要」類型。

## 安裝

1. 確保已安裝 Python 和 `uv`。
2. 安裝依賴：
   ```bash
   uv sync
   ```

## 環境設定

1. 複製 `.env.example` 為 `.env` 並填入以下資訊：
   - `LINE_CHANNEL_ACCESS_TOKEN` & `LINE_CHANNEL_SECRET`: 從 LINE Developers Console 取得。
   - `GEMINI_API_KEY`: 從 [Google AI Studio](https://aistudio.google.com/) 取得。
   - `NOTION_TOKEN` & `NOTION_DATABASE_ID`: 從 Notion 整合頁面取得。
   - `GOOGLE_SHEET_ID`: 目標 Google 試算表的 ID。

2. **Google Sheets 設定**:
   - 建立一個 Google Service Account 並下載 JSON 憑證金鑰。
   - 將該金鑰檔案重新命名為 `service-account.json` 並放在專案根目錄（此檔案已被 git 忽略）。
   - 在 Google 試算表中，將編輯權限共用給 Service Account 的 Email。

3. **Notion 資料庫設定**:
   - 請確保資料庫包含以下欄位：
     - `Name`: 標題 (Title)
     - `Content`: 純文字 (Rich Text)
     - `Summary`: 純文字 (Rich Text)
     - `Type`: 選項 (Select)

## 執行

執行以下指令啟動伺服器：

```bash
uv run uvicorn main:app --reload
```

## 部署與測試 (使用 ngrok)

1. 啟動 ngrok：
   ```bash
   uv run python start_ngrok.py
   ```
2. 複製輸出的 Webhook URL 並貼到 LINE Developers Console。
