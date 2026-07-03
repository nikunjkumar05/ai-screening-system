from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel
from google.genai import Client

from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

client = Client(api_key=GEMINI_API_KEY)

class RAGDocument(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

class RAGEngine:
    def __init__(self):
        self.documents: List[RAGDocument] = []
        self.embeddings: np.ndarray = np.array([])

    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> None:
        doc = RAGDocument(text=text, metadata=metadata or {})
        self.documents.append(doc)

    async def embed_text(self, text: str) -> np.ndarray:
        response = await client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return np.array(response.embeddings[0].values)

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    async def generate_answer(self, query: str, context_chunks: List[str]) -> str:
        context = "\n".join(context_chunks)

        prompt = f"""
        Use the following context to answer the question. If the context doesn't contain 
        the answer, say so clearly.
        
        Context:
        {context}
        
        Question:
        {query}
        """

        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        return response.text