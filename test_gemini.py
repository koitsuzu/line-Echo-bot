import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API Key found")
    exit()

genai.configure(api_key=api_key)

print("Listing models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)

model_name = 'models/gemini-1.5-flash'
print(f"\nUsing model: {model_name}")
model = genai.GenerativeModel(model_name)

# Create a dummy audio file (or use an existing one if I had one, but I'll create a text file mimicking code flow to check model instantiation, 
# actually I really need a real audio file to test audio. 
# Since I cannot record audio here, I will try to upload a small dummy file or just check the model capabilities print first.)

try:
    print("Testing text generation first...")
    response = model.generate_content("Hello")
    print(f"Text response: {response.text}")
except Exception as e:
    print(f"Text generation failed: {e}")
