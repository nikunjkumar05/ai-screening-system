#!/usr/bin/env python3
"""
Knowledge Base Ingestion Script

Process textbook PDFs into LanceDB vector store for RAG retrieval.

Usage:
    python -m backend.app.services.ingest_kb --role "AI/ML Engineer" --pdf path/to/book.pdf
    python -m backend.app.services.ingest_kb --role "Backend Engineer" --pdf book1.pdf book2.pdf
"""

import argparse
import asyncio
import sys
from pathlib import Path

import pymupdf as fitz

# ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.app.services.chunker import chunk_text
from backend.app.services.rag_engine import RAGEngine


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


async def ingest(role: str, pdf_paths: list[str], chunk_size: int = 800, overlap: int = 150):
    rag = RAGEngine(role=role)

    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        if not path.exists():
            print(f"[SKIP] File not found: {pdf_path}")
            continue

        print(f"[READ] Extracting text from {path.name}...")
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text.strip():
            print(f"[SKIP] No text extracted from {path.name}")
            continue

        print(f"[CHUNK] Splitting into chunks (size={chunk_size}, overlap={overlap})...")
        chunks = chunk_text(raw_text, source=path.name, chunk_size=chunk_size, overlap=overlap)
        print(f"[CHUNK] Created {len(chunks)} chunks")

        for chunk in chunks:
            rag.add_document(text=chunk["text"], source=chunk["source"], page=chunk.get("chunk_index", 0))

    print(f"[EMBED] Generating embeddings and storing in LanceDB...")
    await rag.build_embeddings()

    print(f"[DONE] Knowledge base ingested for role: {role}")
    print(f"       Table: {rag.table_name}")
    print(f"       LanceDB dir: {rag._table_name()}")


def main():
    parser = argparse.ArgumentParser(description="Ingest textbook PDFs into LanceDB")
    parser.add_argument("--role", required=True, help="Job role (e.g., 'AI/ML Engineer', 'Backend Engineer')")
    parser.add_argument("--pdf", nargs="+", required=True, help="Path(s) to textbook PDF files")
    parser.add_argument("--chunk-size", type=int, default=800, help="Chunk size in characters (default: 800)")
    parser.add_argument("--overlap", type=int, default=150, help="Overlap between chunks (default: 150)")
    args = parser.parse_args()

    asyncio.run(ingest(args.role, args.pdf, args.chunk_size, args.overlap))


if __name__ == "__main__":
    main()
