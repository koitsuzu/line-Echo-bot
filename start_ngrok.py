import os
import sys
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()

# Check for token in env or ask user
token = os.getenv("NGROK_AUTHTOKEN")
if not token:
    print("錯誤: 未設定 NGROK_AUTHTOKEN。")
    print("請前往 https://dashboard.ngrok.com/get-started/your-authtoken 取得 Token，")
    print("並將其加入 .env 檔案中： NGROK_AUTHTOKEN=你的token")
    sys.exit(1)

ngrok.set_auth_token(token)

# Provide a simpler way for the user to copy the URL
try:
    # Open a HTTP tunnel on the default port 8000
    # <NgrokTunnel: "https://<public_sub>.ngrok.io" -> "http://localhost:8000">
    public_url = ngrok.connect(8000).public_url
    print(f" * nmrok tunnel \"{public_url}\" -> \"http://127.0.0.1:8000\"")
    print(f" * Webhook URL: {public_url}/callback")
    print("請將上方的 Webhook URL 複製到 LINE Developers Console 中。")
    
    # Keep the script running
    print("按下 Ctrl+C 停止 tunnel...")
    ngrok_process = ngrok.get_ngrok_process()
    ngrok_process.proc.wait()
except Exception as e:
    print(f"發生錯誤: {e}")
