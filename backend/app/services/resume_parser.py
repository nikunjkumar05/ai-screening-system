from typing import Dict, Any
import json
from pathlib import Path
import pymupdf as fitz
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_mistral_client = None

def _get_mistral_client():
    global _mistral_client
    if _mistral_client is None:
        from mistralai.client import Mistral
        api_key = os.getenv("MISTRAL_API_KEY", "")
        if api_key:
            _mistral_client = Mistral(api_key=api_key)
    return _mistral_client

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
        client = _get_mistral_client()
        if not client:
            return {"error": "Mistral API key not configured"}

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

        response = await client.chat.complete_async(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # handle None or empty response
        if not response or not response.choices:
            return {"error": "Failed to extract info from resume"}

        raw_text = response.choices[0].message.content

        # fallback: extract JSON from response text
        try:
            text = raw_text.strip()
            # handle markdown code blocks
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {"raw_text": raw_text}

    async def process_resume(self, file_path: str, filename: str = "") -> Dict[str, Any]:
        text = self.extract_text_from_file(file_path, filename)
        if not text.strip():
            return {"error": "Could not extract text from resume"}
        structured_info = await self.extract_structured_info(text)
        return structured_info
