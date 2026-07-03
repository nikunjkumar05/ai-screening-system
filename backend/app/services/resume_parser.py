from typing import Dict, Any, Optional
from pathlib import Path
import pymupdf as fitz
from dotenv import load_dotenv
import os
from google.genai import Client

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

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

    async def extract_structured_info(self, resume_text: str) -> Dict[str, Any]:
        prompt = f"""
        Extract and structure information from this resume text. 
        Return JSON with these fields: name, email, phone, location, experience_years, 
        education, skills, profile_summary. For numbers, use integers where appropriate.
        
        Resume text:
        {resume_text}
        """

        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        return response.parsed

    async def process_resume(self, pdf_path: str) -> Dict[str, Any]:
        text = self.extract_text_from_pdf(pdf_path)
        structured_info = await self.extract_structured_info(text)
        return structured_info