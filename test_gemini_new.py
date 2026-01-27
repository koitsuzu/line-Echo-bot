from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API Key found")
    exit()

client = genai.Client(api_key=api_key)

print("Text generation test with gemini-2.0-flash (or 1.5-flash)...")
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Hello, tell me a joke.'
    )
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
