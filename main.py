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
import tempfile
import pathlib

# Load environment variables
load_dotenv()

# Get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
gemini_api_key = os.getenv('GEMINI_API_KEY', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if gemini_api_key is None:
    print('Specify GEMINI_API_KEY as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# Configure Gemini Client
client = genai.Client(api_key=gemini_api_key)

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
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
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

        # Generate content using Gemini 2.5
        print("Transcribing with Gemini 2.5-flash...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp4"),
                        types.Part.from_text(text="Transcribe this audio exactly as spoken.")
                    ]
                )
            ]
        )
        
        transcript = response.text
        print(f"Transcript: {transcript}")

        # Reply with the transcribed text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=transcript if transcript else "無法辨識語音內容")
        )
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
