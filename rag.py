"""Chhota sa BM25 retriever (pure Python, koi vector DB nahi chahiye).
Baad mein ChromaDB + embeddings se replace kar sakte ho; interface wahi rahega."""
import math
import re
from collections import Counter

from . import db

TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str):
    return TOKEN.findall(text.lower())


def chunk_text(text: str, size: int = 900, overlap: int = 150):
    text = re.sub(r"\s+", " ", text).strip()
    chunks, i = [], 0
    while i < len(text):
        end = min(i + size, len(text))
        if end < len(text):
            cut = max(text.rfind(". ", i, end), text.rfind("? ", i, end))
            if cut > i + size // 2:
                end = cut + 1
        chunks.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return [c for c in chunks if len(c) > 30]


def save_doc(name: str, text: str) -> int:
    chunks = chunk_text(text)
    with db.conn() as c:
        cur = c.execute("INSERT INTO docs(name) VALUES (?)", (name,))
        doc_id = cur.lastrowid
        c.executemany("INSERT INTO chunks(doc_id, text) VALUES (?,?)", [(doc_id, ch) for ch in chunks])
    return doc_id


def _load(doc_ids):
    with db.conn() as c:
        if doc_ids:
            q = ",".join("?" * len(doc_ids))
            rows = c.execute(
                f"SELECT c.id, c.doc_id, c.text, d.name FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.doc_id IN ({q})",
                doc_ids,
            ).fetchall()
        else:
            rows = c.execute("SELECT c.id, c.doc_id, c.text, d.name FROM chunks c JOIN docs d ON d.id=c.doc_id").fetchall()
    return [dict(r) for r in rows]


def search(query: str, doc_ids=None, k: int = 5):
    rows = _load(doc_ids)
    if not rows:
        return []
    docs = [tokenize(r["text"]) for r in rows]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n or 1
    df = Counter()
    for d in docs:
        df.update(set(d))
    q = tokenize(query)
    k1, b = 1.5, 0.75
    scored = []
    for r, d in zip(rows, docs):
        tf = Counter(d)
        score = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for s, r in scored[:k] if s > 0]
    return top or [r for _, r in scored[:k]]


def sample_context(doc_ids=None, max_chars: int = 9000):
    """Quiz/flashcards ke liye notes ka spread-out sample."""
    rows = _load(doc_ids)
    if not rows:
        return ""
    step = max(1, len(rows) * 900 // max_chars)
    out, total = [], 0
    for r in rows[::step]:
        if total + len(r["text"]) > max_chars:
            break
        out.append(r["text"])
        total += len(r["text"])
    return "\n\n".join(out)
