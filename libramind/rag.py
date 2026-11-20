"""
rag.py – Embedding-based retrieval for books and library policies.

Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings.
Stores vectors in ChromaDB PersistentClient.
Falls back to numpy cosine similarity if ChromaDB import fails.
"""
from __future__ import annotations

import os
import glob
import math
import textwrap
from typing import List, Tuple, Dict, Any

from config import CHROMA_PATH

# ---------------------------------------------------------------------------
# Lazy singleton: sentence-transformer model
# ---------------------------------------------------------------------------
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(texts: List[str]) -> List[List[float]]:
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True).tolist()


# ---------------------------------------------------------------------------
# ChromaDB setup (with numpy fallback)
# ---------------------------------------------------------------------------
USE_CHROMA = True
try:
    import chromadb
    _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
except Exception:
    USE_CHROMA = False

# numpy fallback store: { collection_name: {"ids": [], "embeddings": [], "docs": [], "metas": []} }
_numpy_store: Dict[str, Dict[str, List]] = {}


def _get_or_create_collection(name: str):
    """Return a ChromaDB collection or a dict (numpy fallback)."""
    if USE_CHROMA:
        return _chroma_client.get_or_create_collection(name=name)
    if name not in _numpy_store:
        _numpy_store[name] = {"ids": [], "embeddings": [], "docs": [], "metas": []}
    return _numpy_store[name]


# ---------------------------------------------------------------------------
# Chunking helper for policy documents
# ---------------------------------------------------------------------------
def _chunk_text(text: str, size: int = 400, overlap: int = 50) -> List[str]:
    """Split text into chunks of ~size chars with overlap."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Indexing functions
# ---------------------------------------------------------------------------
def index_books() -> None:
    """Index all books from the SQLite DB into the 'books' ChromaDB collection."""
    from db import get_conn

    conn = get_conn()
    rows = conn.execute(
        "SELECT id, title, author, subject, description FROM books"
    ).fetchall()
    conn.close()

    if not rows:
        return

    collection = _get_or_create_collection("books")
    documents = [
        f"{r['title']} by {r['author']}. Subject: {r['subject']}. {r['description'] or ''}"
        for r in rows
    ]
    ids = [str(r["id"]) for r in rows]
    embeddings = _embed(documents)
    metadatas = [{"book_id": r["id"]} for r in rows]

    if USE_CHROMA:
        # Upsert to avoid duplicates on re-index
        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    else:
        store = collection
        store["ids"] = ids
        store["embeddings"] = embeddings
        store["docs"] = documents
        store["metas"] = metadatas


def index_policies() -> None:
    """Chunk and index all policy markdown files into the 'policies' collection."""
    policies_dir = os.path.join("data", "policies")
    files = glob.glob(os.path.join(policies_dir, "*.md"))

    if not files:
        return

    collection = _get_or_create_collection("policies")
    all_ids, all_embeddings, all_docs, all_metas = [], [], [], []

    for filepath in files:
        source = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = _chunk_text(text, size=400, overlap=50)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{source}_{i}"
            all_ids.append(chunk_id)
            all_docs.append(chunk)
            all_metas.append({"source": source})

    all_embeddings = _embed(all_docs)

    if USE_CHROMA:
        collection.upsert(ids=all_ids, embeddings=all_embeddings, documents=all_docs, metadatas=all_metas)
    else:
        store = collection
        store["ids"] = all_ids
        store["embeddings"] = all_embeddings
        store["docs"] = all_docs
        store["metas"] = all_metas


def add_book_to_index(book: Dict[str, Any]) -> None:
    """Add or update a single book in the 'books' collection."""
    collection = _get_or_create_collection("books")
    doc = (
        f"{book['title']} by {book['author']}. "
        f"Subject: {book['subject']}. {book.get('description', '')}"
    )
    book_id = str(book["id"])
    embedding = _embed([doc])

    if USE_CHROMA:
        collection.upsert(
            ids=[book_id],
            embeddings=embedding,
            documents=[doc],
            metadatas=[{"book_id": book["id"]}],
        )
    else:
        store = collection
        if book_id in store["ids"]:
            idx = store["ids"].index(book_id)
            store["embeddings"][idx] = embedding[0]
            store["docs"][idx] = doc
            store["metas"][idx] = {"book_id": book["id"]}
        else:
            store["ids"].append(book_id)
            store["embeddings"].append(embedding[0])
            store["docs"].append(doc)
            store["metas"].append({"book_id": book["id"]})


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------
def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_search_books(query: str, k: int = 5) -> List[Tuple[int, float]]:
    """
    Search the 'books' collection.
    Returns list of (book_id, score) sorted by relevance descending.
    """
    q_emb = _embed([query])[0]
    collection = _get_or_create_collection("books")

    if USE_CHROMA:
        results = collection.query(
            query_embeddings=[q_emb],
            n_results=min(k, collection.count()) if collection.count() > 0 else 1,
            include=["metadatas", "distances"],
        )
        out = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            score = 1 - dist  # ChromaDB returns L2 distance; convert roughly to similarity
            out.append((meta["book_id"], round(score, 4)))
        return out
    else:
        store = collection
        if not store["embeddings"]:
            return []
        scored = [
            (store["metas"][i]["book_id"], _cosine_similarity(q_emb, store["embeddings"][i]))
            for i in range(len(store["embeddings"]))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


def search_policies(question: str, k: int = 3) -> List[Dict[str, str]]:
    """
    Search the 'policies' collection.
    Returns list of {"text": ..., "source": ...}.
    """
    q_emb = _embed([question])[0]
    collection = _get_or_create_collection("policies")

    if USE_CHROMA:
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_embeddings=[q_emb],
            n_results=min(k, count),
            include=["documents", "metadatas"],
        )
        out = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            out.append({"text": doc, "source": meta["source"]})
        return out
    else:
        store = collection
        if not store["embeddings"]:
            return []
        scored = [
            (i, _cosine_similarity(q_emb, store["embeddings"][i]))
            for i in range(len(store["embeddings"]))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"text": store["docs"][i], "source": store["metas"][i]["source"]}
            for i, _ in scored[:k]
        ]
