import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, AudioMessage
)
from dotenv import load_dotenv
from google import genai
from google.genai import types
from notion_client import Client
import gspread
from google.oauth2.service_account import Credentials
import tempfile
import pathlib
import datetime
import json

# Load environment variables
load_dotenv()

# Get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gemini_api_key = os.getenv('GEMINI_API_KEY', None)
notion_token = os.getenv('NOTION_TOKEN', None)
notion_db_id = os.getenv('NOTION_DATABASE_ID', None)
gs_id = os.getenv('GOOGLE_SHEET_ID', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if gemini_api_key is None:
    print('Specify GEMINI_API_KEY as environment variable.')
    sys.exit(1)
if notion_token is None:
    print('Specify NOTION_TOKEN as environment variable.')
    sys.exit(1)
if notion_db_id is None:
    print('Specify NOTION_DATABASE_ID as environment variable.')
    sys.exit(1)
if gs_id is None:
    print('Specify GOOGLE_SHEET_ID as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# Configure Gemini Client
client = genai.Client(api_key=gemini_api_key)

# Configure Notion Client
notion = Client(auth=notion_token)

def log_to_notion(transcript: str, summary: str, log_type: str = "語音摘要"):
    """Logs the transcript and summary to the Notion database."""
    print(f"DEBUG: Attempting to log to Notion. DB_ID: {notion_db_id}, Type: {log_type}")
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res = notion.pages.create(
            parent={"database_id": notion_db_id},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": f"{log_type} - {now}"
                            }
                        }
                    ]
                },
                "Content": { 
                    "rich_text": [
                        {
                            "text": {
                                "content": transcript
                            }
                        }
                    ]
                },
                "Summary": { 
                    "rich_text": [
                        {
                            "text": {
                                "content": summary
                            }
                        }
                    ]
                },
                "Type": {
                    "select": {
                        "name": log_type
                    }
                }
            }
        )
        print("Successfully logged to Notion.")
    except Exception as e:
        print(f"ERROR: Notion logging failed: {type(e).__name__}: {e}")

# Configure Google Sheets Client
def log_to_sheets(transcript: str, summary: str, log_type: str = "語音摘要"):
    """Logs the transcript and summary to the Google Sheet."""
    print(f"DEBUG: Attempting to log to Google Sheets. Sheet_ID: {gs_id}, Type: {log_type}")
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("service-account.json", scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(gs_id)
        wks = sh.get_worksheet(0) # 第一張工作表
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 欄位：時間, 內容/逐字稿, 摘要, 類型
        wks.append_row([now, transcript, summary, log_type])
        print("Successfully logged to Google Sheets.")
    except Exception as e:
        print(f"ERROR: Google Sheets logging failed: {type(e).__name__}: {e}")

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/callback")
async def callback(request: Request):
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body = await request.body()
    body_text = body.decode('utf-8')

    # handle webhook body
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    
    try:
        print("Summarizing text with Gemini 2.5-flash...")
        prompt = f"""
        請閱讀以下這段文字，並提供一份簡短的繁體中文摘要。
        請務必以 JSON 格式回傳，格式如下：
        {{
          "transcript": "原始文字內容",
          "summary": "簡短的繁體中文內容摘要"
        }}
        不要包含任何額外的 Markdown 標記 (如 ```json) 或解釋。
        
        文字內容：
        {text}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        raw_text = response.text.strip()
        # 清理 JSON
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        try:
            data = json.loads(raw_text)
            summary = data.get("summary", "摘要產生失敗")
        except Exception as json_err:
            print(f"JSON Parsing failed for text: {json_err}")
            summary = "摘要產生失敗"

        # 回傳摘要給用戶
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"【文字摘要】\n{summary}")
        )

        # 儲存到 Notion 與 Google Sheets
        log_to_notion(text, summary, "文字摘要")
        log_to_sheets(text, summary, "文字摘要")
        
    except Exception as e:
        print(f"Error handling text message: {e}")
        # 如果失敗，至少 Echo 原文
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"【文字摘要失敗】\n{text}")
        )

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    
    # Save audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_file_path = tf.name

    try:
        # Read file bytes
        with open(temp_file_path, "rb") as f:
            audio_bytes = f.read()

        # Prepare Gemini content request with JSON output schema
        print("Transcribing and summarizing with Gemini 2.5-flash...")
        prompt = """
        請將這段語音轉寫為繁體中文，並提供一份簡短的摘要。
        請務必以 JSON 格式回傳，格式如下：
        {
          "transcript": "完整的繁體中文逐字稿內容",
          "summary": "簡短的繁體中文內容摘要"
        }
        不要包含任何額外的 Markdown 標記 (如 ```json) 或解釋。
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp4"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        
        # Clean up JSON response if model added backticks
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3].strip()
            
        try:
            data = json.loads(raw_text)
            transcript = data.get("transcript", "")
            summary = data.get("summary", "")
        except Exception as json_err:
            print(f"JSON Parsing failed: {json_err}. Raw text: {raw_text}")
            transcript = raw_text
            summary = "摘要產生失敗"

        print(f"Transcript: {transcript[:50]}...")
        print(f"Summary: {summary[:50]}...")

        # Reply with the transcribed text and summary
        reply_message = f"【逐字稿】\n{transcript}\n\n【摘要】\n{summary}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message if transcript else "無法辨識語音內容")
        )

        # Log to Notion and Google Sheets
        if transcript:
            log_to_notion(transcript, summary)
            log_to_sheets(transcript, summary)
    except Exception as e:
        print(f"Error handling audio message: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"抱歉，語音轉文字失敗 (Error: {str(e)})")
        )
    finally:
        # Clean up temporary file locally
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
