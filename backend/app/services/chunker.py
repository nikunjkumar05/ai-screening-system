from typing import List, Dict, Optional


def chunk_text(
    text: str,
    source: str = "",
    chunk_size: int = 800,
    overlap: int = 150,
) -> List[Dict]:
    """
    Split text into overlapping chunks.

    Args:
        text: Full document text
        source: Source document name for metadata
        chunk_size: Target characters per chunk (default 800)
        overlap: Character overlap between consecutive chunks (default 150)

    Returns:
        List of dicts with text, source, and page metadata
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = start + chunk_size

        # try to break at a sentence boundary
        if end < len(text):
            # look for sentence endings within the last 200 chars of the chunk
            look_back = min(200, chunk_size // 3)
            candidate = text[start + chunk_size - look_back : end]
            last_period = candidate.rfind(".")
            last_newline = candidate.rfind("\n")
            break_at = max(last_period, last_newline)
            if break_at > 0:
                end = start + chunk_size - look_back + break_at + 1

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunks.append({
                "text": chunk_text_str,
                "source": source,
                "chunk_index": chunk_idx,
            })
            chunk_idx += 1

        start = end - overlap
        if start >= len(text):
            break

    return chunks
