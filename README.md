# LINE 多功能 AI 摘要助手

這是一個功能強大的 LINE 機器人，整合了 Google Gemini 2.5-flash 的多模態分析能力，能自動處理、摘要並同步多種格式的訊息至雲端平台。

## 🚀 核心功能描述

### 1. 語音逐字稿與摘要 (`語音摘要`)
- **功能**: 接收語音訊息 (.m4a)，自動轉錄為繁體中文逐字稿，並產生重點摘要。
- **儲存**: 同步至 Notion 資料庫與 Google Sheets。

### 2. 長文字摘要 (`文字摘要`)
- **功能**: 接收文字訊息，自動分析內容並回傳精簡摘要。

### 3. 圖片辨識與內容分析 (`圖片摘要`)
- **功能**: 接收圖片後，辨識圖中文字或描述場景。
- **雲端備份**: 透過 **OAuth 2.0** 自動將圖片存至您的 **Google Drive** 特定資料夾。

### 4. 網頁內容摘要 (`網頁摘要`)
- **功能**: 自動偵測訊息中的 URL，爬取一般網頁內容後產生摘要。

### 5. 社群貼文分析 (`社群爬蟲`) [NEW]
- **功能**: 偵測 Facebook 與 Instagram 連結，呼叫 **Apify Crawler** 抓取貼文內容與評論，並產出精確摘要。
- **優勢**: 解決一般爬蟲無法讀取社群平台（如 IG/FB）內容的問題。

---

## 🛠️ 技術棧
- **後端**: FastAPI (Python)
- **AI**: Google Gemini 2.5-flash
- **資料庫**: Notion API / Google Sheets API
- **雲端備份**: Google Drive API (OAuth 2.0)
- **爬蟲技術**: `httpx` + `BeautifulSoup4` & **Apify Client SDK**

---

## ⚙️ 環境設定與安裝

### 1. 基礎安裝
```bash
uv sync
```

### 2. 環境變數 (.env)
請參考 `.env.example` 填寫：
- `LINE_CHANNEL_ACCESS_TOKEN` / `SECRET`
- `GEMINI_API_KEY`
- `NOTION_TOKEN` / `DATABASE_ID`
- `GOOGLE_SHEET_ID`
- `GOOGLE_DRIVE_FOLDER_ID`
- `APIFY_API_TOKEN` (用於社群爬蟲)

---

## 🎬 執行指令
```bash
# 啟動伺服器
uv run uvicorn main:app --reload
```
