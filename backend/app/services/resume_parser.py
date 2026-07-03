from typing import Dict, Any
import json
from pathlib import Path
import pymupdf as fitz
from dotenv import load_dotenv
import os
from google.genai import Client

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = None
if GEMINI_API_KEY:
    client = Client(api_key=GEMINI_API_KEY)


class ResumeParserService:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        if filename.lower().endswith(".pdf"):
            return self.extract_text_from_pdf(file_path)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    async def extract_structured_info(self, resume_text: str) -> Dict[str, Any]:
        if not client:
            return {"error": "Gemini API key not configured"}

        prompt = (
            "Extract and structure information from this resume text.\n"
            "Return ONLY valid JSON with these fields:\n"
            "- name (string)\n"
            "- email (string)\n"
            "- phone (string)\n"
            "- location (string)\n"
            "- experience_years (integer)\n"
            "- education (string)\n"
            "- skills (comma-separated string)\n"
            "- profile_summary (string)\n\n"
            f"Resume text:\n{resume_text}"
        )

        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )

        # handle None or empty response
        if not response or not response.text:
            return {"error": "Failed to extract info from resume"}

        # try parsed first, then manual JSON parse from text
        if response.parsed:
            return response.parsed

        # fallback: extract JSON from response text
        try:
            text = response.text.strip()
            # handle markdown code blocks
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw_text": response.text}

    async def process_resume(self, file_path: str, filename: str = "") -> Dict[str, Any]:
        text = self.extract_text_from_file(file_path, filename)
        if not text.strip():
            return {"error": "Could not extract text from resume"}
        structured_info = await self.extract_structured_info(text)
        return structured_info
