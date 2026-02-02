import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, AudioMessage, ImageMessage, FlexSendMessage
from dotenv import load_dotenv
from google import genai
from google.genai import types
from notion_client import Client
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import pathlib
import datetime
import json
import re
import httpx
from bs4 import BeautifulSoup
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

# Get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gemini_api_key = os.getenv('GEMINI_API_KEY', None)
notion_token = os.getenv('NOTION_TOKEN', None)
notion_db_id = os.getenv('NOTION_DATABASE_ID', None)
gs_id = os.getenv('GOOGLE_SHEET_ID', None)
drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', None)
apify_token = os.getenv('APIFY_API_TOKEN', None)
apify_fb_actor = os.getenv('APIFY_FACEBOOK_ACTOR_ID', 'apify/facebook-posts-scraper')
apify_ig_actor = os.getenv('APIFY_IG_ACTOR_ID', 'apify/instagram-scraper')

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if apify_token is None:
    print('Specify APIFY_API_TOKEN as environment variable.')
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
if drive_folder_id is None:
    print('Specify GOOGLE_DRIVE_FOLDER_ID as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# Configure Gemini Client
client = genai.Client(api_key=gemini_api_key)

# Configure Notion Client
notion = Client(auth=notion_token)

# Configure Apify Client
apify_client = ApifyClient(apify_token)

def create_flex_message(title: str, summary: str, url: str = None) -> FlexSendMessage:
    """Creates a compact 'Inspiration Assistant' Flex Message."""
    contents = {
      "type": "bubble",
      "body": {
        "type": "box",
        "layout": "horizontal",
        "contents": [
          {
            "type": "box",
            "layout": "vertical",
            "contents": [
              {
                "type": "text",
                "text": "🤖",
                "size": "24px",
                "align": "center",
                "gravity": "center"
              }
            ],
            "width": "40px",
            "height": "40px",
            "backgroundColor": "#F2F2F2",
            "cornerRadius": "20px",
            "justifyContent": "center",
            "alignItems": "center",
            "flex": 0
          },
          {
            "type": "box",
            "layout": "vertical",
            "contents": [
              {
                "type": "box",
                "layout": "baseline",
                "contents": [
                  {
                    "type": "text",
                    "text": "靈感助理",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#000000",
                    "flex": 0
                  },
                  {
                    "type": "text",
                    "text": "剛剛",
                    "size": "xs",
                    "color": "#999999",
                    "align": "end",
                    "flex": 1
                  }
                ],
                "margin": "none"
              },
              {
                "type": "text",
                "text": title if title else "無標題",
                "weight": "bold",
                "size": "md",
                "margin": "xs",
                "wrap": True,
                "color": "#000000"
              },
              {
                "type": "text",
                "text": summary if summary else "無摘要內容",
                "size": "sm",
                "color": "#333333",
                "wrap": True,
                "margin": "md",
                "lineSpacing": "5px"
              }
            ],
            "paddingStart": "md",
            "flex": 1
          }
        ],
        "paddingAll": "lg",
        "alignItems": "flex-start"
      }
    }
    
    # If there's a URL, we can add it as a tap action on the whole bubble or keep it as is.
    # The user template didn't have a button, so I'll add a tap action to the bubble for the URL.
    if url:
        contents["action"] = {
            "type": "uri",
            "label": "打開連結",
            "uri": url
        }

    return FlexSendMessage(alt_text=f"【靈感助理】{title}", contents=contents)

def log_to_notion(transcript: str, summary: str, log_type: str = "語音摘要"):
    """Logs the transcript and summary to the Notion database."""
    print(f"DEBUG: Attempting to log to Notion. DB_ID: {notion_db_id}, Type: {log_type}")
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        # Notion doesn't use these scopes, but we maintain the service account logic for sheets/notion if needed
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
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_json:
            print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not found in environment variables.")
            return

        service_account_info = json.loads(service_account_json)
        creds = ServiceAccountCredentials.from_service_account_info(service_account_info, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(gs_id)
        wks = sh.get_worksheet(0) # 第一張工作表
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 欄位：時間, 內容/逐字稿, 摘要, 類型
        wks.append_row([now, transcript, summary, log_type])
        print("Successfully logged to Google Sheets.")
    except Exception as e:
        print(f"ERROR: Google Sheets logging failed: {type(e).__name__}: {e}")

# Configure Google Drive Client
def upload_to_drive(file_path: str, filename: str):
    """Uploads a file to Google Drive using OAuth token and returns the webViewLink."""
    try:
        # Use token.json for OAuth authentication (Uploader's identity)
        if not os.path.exists('token.json'):
            print("ERROR: token.json not found. Please run generate_token.py first.")
            return None
            
        creds = UserCredentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': filename,
            'parents': [drive_folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='image/jpeg', resumable=True)
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        print(f"ERROR: Google Drive upload failed: {type(e).__name__}: {e}")
        return None

def scrape_webpage(url: str):
    """Scrapes the content of a webpage and returns the text."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean up whitespaces
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:10000] # Limit content for Gemini
    except Exception as e:
        print(f"Scraping failed for {url}: {e}")
        return None

def run_apify_actor(actor_id: str, run_input: dict):
    """Runs an Apify actor and retrieves the last dataset item."""
    try:
        print(f"Running Apify Actor: {actor_id}")
        run = apify_client.actor(actor_id).call(run_input=run_input)
        
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return None, "No dataset ID found."
            
        # Get the items
        items = apify_client.dataset(dataset_id).list_items().items
        
        if items:
            return items, None
        return None, "Dataset is empty."
    except Exception as e:
        error_msg = str(e)
        print(f"Apify Actor failed: {error_msg}")
        return None, error_msg

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
    text = event.message.text.strip()
    
    # URL Detection
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    
    if urls:
        # We only summarize the first URL found for simplicity
        target_url = urls[0]
        
        # Check for Social Media URLs
        is_social_media = False
        actor_id = None
        apify_input = {}
        
        if any(domain in target_url for domain in ["facebook.com", "fb.watch", "fb.me"]):
            is_social_media = True
            actor_id = apify_fb_actor
            # Different actors expect different inputs, assuming facebook-posts-scraper logic (startUrls)
            apify_input = {
                "startUrls": [{"url": target_url}],
                "resultsLimit": 1
            }
            
        elif any(domain in target_url for domain in ["instagram.com", "instagr.am"]):
            is_social_media = True
            actor_id = apify_ig_actor
            # apify/instagram-scraper usually takes directUrls
            apify_input = {
                "directUrls": [target_url],
                "resultsLimit": 1
            }
        
        if is_social_media:
            # We must use reply_token immediately or it might expire/be used elsewhere
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="正在啟動爬蟲分析社群貼文，請稍候... (可能需要 15-30 秒)")
            )
            
            try:
                print(f"Detected Social Media URL: {target_url}. Using Apify...")
                
                # Note: reply_token is invalid after a short time, so sending a push message might be needed for long tasks.
                # But for now we try to finish within timeout or just let the first reply be "processing" 
                # and then push the result if we had user ID. echo bot logic uses reply_token which expires.
                # Standard reply token valid for ~30 sec. Apify might take longer.
                # However, for this architecture, we will attempt to do it synchronously.
                
                scraped_data, error_msg = run_apify_actor(actor_id, apify_input)
                
                if scraped_data:
                    # Convert data to string for Gemini
                    data_str = json.dumps(scraped_data, ensure_ascii=False)[:30000] # Limit size
                    
                    print("Summarizing social content with Gemini 2.5-flash...")
                    prompt = f"""
                    請閱讀以下社群貼文的爬蟲資料 (JSON 格式)，並提供一份繁體中文摘要。
                    重點請放在貼文的正文內容 (text/caption) 與重要留言。
                    請務必以 JSON 格式回傳，格式如下：
                    {{
                        "summary": "簡短的貼文內容摘要"
                    }}
                    不要包含任何額外的 Markdown 標記。
                    
                    爬蟲資料：
                    {data_str}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    
                    raw_text = response.text.strip()
                        
                    try:
                        data = json.loads(raw_text)
                        summary = data.get("summary", "社群摘要產生失敗")
                    except Exception as json_err:
                        print(f"JSON Parsing failed: {json_err}")
                        summary = "社群摘要產生失敗"

                    user_id = event.source.user_id
                    if user_id:
                        flex_msg = create_flex_message(
                            title="社群貼文摘要",
                            summary=summary,
                            url=target_url
                        )
                        line_bot_api.push_message(user_id, flex_msg)
                    
                    log_to_notion(target_url, summary, "社群爬蟲")
                    log_to_sheets(target_url, summary, "社群爬蟲")
                    return
                else:
                    print(f"Apify returned no data. Reason: {error_msg}")
                    user_id = event.source.user_id
                    if user_id:
                        # Translate some common Apify errors for the user
                        user_friendly_error = "社群爬蟲未能取得資料。"
                        if "rent a paid Actor" in str(error_msg):
                            user_friendly_error = "此 Apify 爬蟲（Actor）需要付費或試用期已過，請前往 Apify Console 處理或更換免費爬蟲。"
                        elif "Actor with this name was not found" in str(error_msg):
                            user_friendly_error = f"找不到指定的爬蟲：{actor_id}，請檢查拼字。"
                        
                        line_bot_api.push_message(user_id, TextSendMessage(text=user_friendly_error))
                
                return # Important: Stop here regardless of success/fail
            except Exception as e:
                print(f"Error handling Social Media URL: {e}")
                user_id = event.source.user_id
                if user_id:
                    line_bot_api.push_message(user_id, TextSendMessage(text=f"處理社群連結時發生錯誤: {str(e)}"))
                return

        # Standard Web Scraping (Fallback or non-social URLs)
        if not is_social_media:
            try:
                print(f"Detected URL: {target_url}. Scraping content...")
                web_content = scrape_webpage(target_url)
                
                if web_content:
                    print("Summarizing webpage with Gemini 2.5-flash...")
                prompt = f"""
                請閱讀以下這段網頁內容，並提供一份簡短的繁體中文摘要。
                請務必以 JSON 格式回傳，格式如下：
                {{
                  "summary": "簡短的網頁內容摘要"
                }}
                不要包含任何額外的 Markdown 標記 (如 ```json) 或解釋。
                
                網頁內容：
                {web_content}
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                
                raw_text = response.text.strip()
                    
                try:
                    data = json.loads(raw_text)
                    summary = data.get("summary", "網頁摘要產生失敗")
                except Exception as json_err:
                    print(f"JSON Parsing failed for webpage: {json_err}")
                    summary = "網頁摘要產生失敗"

                # Reply with summary
                flex_msg = create_flex_message(
                    title="網頁內容摘要",
                    summary=summary,
                    url=target_url
                )
                line_bot_api.reply_message(event.reply_token, flex_msg)

                # Log to Notion and Sheets - Using the URL as the transcript
                log_to_notion(target_url, summary, "網頁摘要")
                log_to_sheets(target_url, summary, "網頁摘要")
                return
            except Exception as e:
                print(f"Error handling URL message: {e}")
                # If scraping fails, we've already used reply_token? No, not yet in this block.
                # But we might want to fall back to normal text processing.
                pass 

    # Normal text summarization
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
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip()
            
        try:
            data = json.loads(raw_text)
            summary = data.get("summary", "摘要產生失敗")
        except Exception as json_err:
            print(f"JSON Parsing failed for text: {json_err}")
            summary = "摘要產生失敗"

        # 回傳摘要給用戶
        # For text summary, we don't really have a URL unless users sent one, but here we treat it as pure text
        flex_msg = create_flex_message(
            title="文字訊息摘要",
            summary=summary,
            url=None
        )
        line_bot_api.reply_message(event.reply_token, flex_msg)

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
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Clean up JSON response
        raw_text = response.text.strip()
            
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
        flex_msg = create_flex_message(
            title="語音訊息摘要",
            summary=summary,
            url=None
        )
        line_bot_api.reply_message(event.reply_token, flex_msg)

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

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    
    # Save image to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        temp_file_path = tf.name

    try:
        # Read image bytes
        with open(temp_file_path, "rb") as f:
            image_bytes = f.read()

        # Generate content using Gemini 2.5 (Multimodal)
        print("Analyzing image with Gemini 2.5-flash...")
        prompt = """
        請分析這張圖片的內容，並提供一份詳細的繁體中文摘要。
        如果是文字請進行辨識，如果是場景請進行描述。
        請務必以 JSON 格式回傳，格式如下：
        {
          "transcript": "圖片中的文字內容（若無文字則描述場景）",
          "summary": "簡短的圖片內容摘要"
        }
        不要包含任何額外的 Markdown 標記 (如 ```json) 或解釋。
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip()
            
        try:
            data = json.loads(raw_text)
            transcript = data.get("transcript", "")
            summary = data.get("summary", "")
        except Exception as json_err:
            print(f"JSON Parsing failed: {json_err}. Raw text: {raw_text}")
            transcript = "圖片內容辨識失敗"
            summary = "圖片摘要產生失敗"

        # Upload to Google Drive
        print("Uploading image to Google Drive...")
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{now_str}.jpg"
        drive_link = upload_to_drive(temp_file_path, filename)

        # Reply with summary and Drive link
        # Use Flex Message
        flex_msg = create_flex_message(
            title="圖片摘要",
            summary=summary,
            url=drive_link # Link to the file in Drive
        )
        line_bot_api.reply_message(event.reply_token, flex_msg)

        # Log to Notion and Google Sheets
        if transcript:
            # 存入時將 Transcript 加上雲端連結
            content_with_link = f"{transcript}\n雲端存檔：{drive_link}" if drive_link else transcript
            log_to_notion(content_with_link, summary, "圖片摘要")
            log_to_sheets(content_with_link, summary, "圖片摘要")

    except Exception as e:
        print(f"Error handling image message: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"抱歉，圖片處理失敗 (Error: {str(e)})")
        )
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
