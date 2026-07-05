from typing import List, Dict, Any, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import lancedb
load_dotenv(Path(__file__).parent.parent.parent / ".env")

LANCEDB_DIR = Path(__file__).parent.parent.parent.parent / "lancedb_data"

_mistral_client = None
_lance_db: Optional[lancedb.DBConnection] = None

def _get_mistral_client():
    global _mistral_client
    if _mistral_client is None:
        from mistralai.client import Mistral
        api_key = os.getenv("MISTRAL_API_KEY", "")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not set in environment")
        _mistral_client = Mistral(api_key=api_key)
    return _mistral_client

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
        # Log warning if table doesn't exist
        if not self._table_exists():
            print(f"[WARN] RAG: LanceDB table '{self.table_name}' does not exist for role '{role}'")

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
        db = _get_lance_db()
        table = self._get_table()
        row = {
            "text": text,
            "source": source or "",
            "page": page or 0,
        }
        if table is None:
            import numpy as np
            # mistral-embed uses 1024 dimensions
            row["vector"] = np.zeros(1024).tolist()
            db.create_table(self.table_name, [row], mode="overwrite")
        else:
            table.add([row])

    async def build_embeddings(self):
        db = _get_lance_db()
        table = self._get_table()
        if table is None:
            return

        client = _get_mistral_client()
        data = table.to_pandas().to_dict("records")

        import asyncio
        batch_size = 50
        vectors = []
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_texts = [row["text"] for row in batch]
            
            try:
                response = await client.embeddings.create_async(
                    model="mistral-embed",
                    inputs=batch_texts,
                )
                for res_data in response.data:
                    vectors.append(res_data.embedding)
            except Exception as e:
                print(f"[ERROR] Failed to embed batch {i//batch_size}: {e}")
                import numpy as np
                for _ in batch:
                    vectors.append(np.zeros(1024).tolist())
            
            # small delay to prevent rate limit
            await asyncio.sleep(2)

        for i, row in enumerate(data):
            row["vector"] = vectors[i]

        db.create_table(self.table_name, data, mode="overwrite")

    async def embed_query(self, text: str) -> list:
        client = _get_mistral_client()
        import asyncio
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.embeddings.create_async(
                    model="mistral-embed",
                    inputs=[text],
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"[WARN] embed_query failed, retrying ({attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(2 ** attempt)

    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        table = self._get_table()
        if table is None:
            print(f"[WARN] RAG: No table found for role '{self.role}' (table: {self.table_name})")
            return []

        try:
            query_vector = await self.embed_query(query)
        except Exception as e:
            print(f"[ERROR] RAG: Failed to embed query: {e}")
            return []

        try:
            results = (
                table.search(query_vector)
                .limit(top_k)
                .select(["text", "source", "page"])
                .to_list()
            )
        except Exception as e:
            print(f"[ERROR] RAG: LanceDB search failed: {e}")
            return []

        chunks = [
            {
                "text": r.get("text", ""),
                "source": r.get("source", ""),
                "page": r.get("page", 0),
                "score": r.get("_distance", 0),
            }
            for r in results
        ]
        print(f"[INFO] RAG: Retrieved {len(chunks)} chunks for role '{self.role}'")
        return chunks

    async def generate_answer(
        self, query: str, context_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        client = _get_mistral_client()
        
        if context_chunks is None:
            prompt = query
        else:
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
        
        import asyncio
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.chat.complete_async(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(f"[WARN] generate_answer failed, retrying ({attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(2 ** attempt)
