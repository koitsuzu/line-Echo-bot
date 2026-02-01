from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Testing API Key: {api_key[:10]}...")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash', # Or 1.5-flash
        contents='Tell me a very short joke.'
    )
    print("Gemini Response SUCCESS:")
    print(response.text)
except Exception as e:
    print(f"Gemini Response FAILED: {e}")
