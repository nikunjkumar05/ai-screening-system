from typing import List, Dict, Any, Optional
import numpy as np
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KB_DIR = Path(__file__).parent.parent.parent / "knowledge_base"

# Lazy client — only initialized when actually needed
_client = None


def _get_client():
    global _client
    if _client is None:
        from google.genai import Client
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Set it in the .env file or as an environment variable."
            )
        _client = Client(api_key=api_key)
    return _client


class RAGEngine:
    def __init__(self, role: str):
        self.role = role
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray = np.array([])
        self._load_if_exists()

    def _embeddings_path(self) -> Path:
        role_key = self.role.lower().replace(" ", "_").replace("/", "-")
        return KB_DIR / "embeddings" / f"{role_key}_embeddings.npy"

    def _metadata_path(self) -> Path:
        role_key = self.role.lower().replace(" ", "_").replace("/", "-")
        return KB_DIR / "embeddings" / f"{role_key}_metadata.json"

    def _load_if_exists(self):
        emb_path = self._embeddings_path()
        meta_path = self._metadata_path()
        if emb_path.exists() and meta_path.exists():
            self.embeddings = np.load(str(emb_path))
            with open(meta_path, "r", encoding="utf-8") as f:
                self.documents = json.load(f)

    def save(self):
        emb_path = self._embeddings_path()
        meta_path = self._metadata_path()
        emb_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(emb_path), self.embeddings)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2)

    def add_document(self, text: str, source: str, page: Optional[int] = None):
        self.documents.append({"text": text, "source": source, "page": page})

    async def build_embeddings(self):
        client = _get_client()
        texts = [d["text"] for d in self.documents]
        embeddings = []
        for t in texts:
            response = await client.aio.models.embed_content(
                model="text-embedding-004",
                contents=t,
            )
            embeddings.append(response.embeddings[0].values)
        self.embeddings = np.array(embeddings)
        self.save()

    async def embed_query(self, text: str) -> np.ndarray:
        client = _get_client()
        response = await client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return np.array(response.embeddings[0].values)

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        return float(
            np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-10)
        )

    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if len(self.documents) == 0:
            return []
        query_emb = await self.embed_query(query)
        scores = []
        for i, doc_emb in enumerate(self.embeddings):
            sim = self.cosine_similarity(query_emb, doc_emb)
            scores.append((i, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for i, score in scores[:top_k]:
            results.append({**self.documents[i], "score": float(score)})
        return results

    async def generate_answer(
        self, query: str, context_chunks: List[Dict[str, Any]]
    ) -> str:
        client = _get_client()
        if context_chunks:
            context = "\n\n".join(
                f"[Source: {c.get('source', 'unknown')}] {c.get('text', '')}"
                for c in context_chunks
            )
        else:
            context = "No retrieved context available."

        prompt = (
            f"Use the following context to answer the question.\n"
            f"If the context doesn't contain enough information, say so clearly.\n"
            f"Always reference the source document when providing information.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{query}"
        )
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return response.text
