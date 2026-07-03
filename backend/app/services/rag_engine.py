from typing import List, Dict, Any, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import lancedb

load_dotenv()

# LanceDB stores data on disk — no more .npy files
LANCEDB_DIR = Path(__file__).parent.parent.parent.parent / "lancedb_data"

# Lazy client
_gemini_client = None
_lance_db: Optional[lancedb.DBConnection] = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google.genai import Client
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        _gemini_client = Client(api_key=api_key)
    return _gemini_client


def _get_lance_db() -> lancedb.DBConnection:
    global _lance_db
    if _lance_db is None:
        LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
        _lance_db = lancedb.connect(str(LANCEDB_DIR))
    return _lance_db


class RAGEngine:
    def __init__(self, role: str):
        self.role = role
        self.table_name = self._table_name()

    def _table_name(self) -> str:
        return self.role.lower().replace(" ", "_").replace("/", "_")

    def _get_table(self):
        db = _get_lance_db()
        try:
            return db.open_table(self.table_name)
        except Exception:
            return None

    def _table_exists(self) -> bool:
        db = _get_lance_db()
        return self.table_name in db.list_tables()

    def add_document(self, text: str, source: str, page: Optional[int] = None):
        """Add a single document (used during ingestion, not live)."""
        db = _get_lance_db()
        table = self._get_table()
        row = {
            "text": text,
            "source": source or "",
            "page": page or 0,
        }
        if table is None:
            # first document — create table with dummy vector to infer schema
            import numpy as np
            row["vector"] = np.zeros(768).tolist()
            db.create_table(self.table_name, [row], mode="overwrite")
        else:
            table.add([row])

    async def build_embeddings(self):
        """Embed all documents in the table and update vectors."""
        db = _get_lance_db()
        table = self._get_table()
        if table is None:
            return

        client = _get_gemini_client()
        data = table.to_pandas().to_dict("records")

        vectors = []
        for row in data:
            response = await client.aio.models.embed_content(
                model="text-embedding-004",
                contents=row["text"],
            )
            vectors.append(response.embeddings[0].values)

        # rebuild table with real vectors
        for i, row in enumerate(data):
            row["vector"] = vectors[i]

        db.create_table(self.table_name, data, mode="overwrite")

    async def embed_query(self, text: str) -> list:
        client = _get_gemini_client()
        response = await client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values

    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        table = self._get_table()
        if table is None:
            return []

        query_vector = await self.embed_query(query)
        results = (
            table.search(query_vector)
            .limit(top_k)
            .select(["text", "source", "page"])
            .to_list()
        )

        return [
            {
                "text": r.get("text", ""),
                "source": r.get("source", ""),
                "page": r.get("page", 0),
                "score": r.get("_distance", 0),
            }
            for r in results
        ]

    async def generate_answer(
        self, query: str, context_chunks: List[Dict[str, Any]]
    ) -> str:
        client = _get_gemini_client()
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
