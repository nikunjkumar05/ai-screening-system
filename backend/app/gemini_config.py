from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

from google.genai import Client

client = Client(api_key=GEMINI_API_KEY)

print(f"Gemini API client initialized with key: {GEMINI_API_KEY[:4]}...")