"""Local RAG store — Plan v1 §4.5 / Plan v2 §4.2 (licences tracked).

No vector database needed on a small offline box: chunks are stored in SQLite
and ranked lexically. Every source keeps its licence and URL so a digest can be
traced back — the plans forbid copying licensed code, not citing it.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional

KNOWN_LICENSES = {
    "cc-by",
    "cc-by-sa",
    "cc0",
    "mit",
    "apache-2",
    "bsd-3",
    "public-domain",
    "internal",
    "unknown",
}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "les", "des", "une", "dans", "pour", "avec", "sur", "est", "sont",
    "في", "من", "على", "إلى", "هذا", "هذه", "اللي", "و", "لا", "ما",
}

TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def tokens(text: str) -> List[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) > 2 and token.lower() not in STOPWORDS
    ]


def split_chunks(body: str, max_chars: int = 1200) -> List[Dict[str, str]]:
    """Split on markdown headings, then on paragraph boundaries."""
    body = (body or "").strip()
    if not body:
        return []
    sections: List[Dict[str, str]] = []
    heading = ""
    buffer: List[str] = []
    for line in body.splitlines():
        if line.strip().startswith("#"):
            if buffer:
                sections.append({"heading": heading, "body": "\n".join(buffer).strip()})
                buffer = []
            heading = line.strip().lstrip("#").strip()
            continue
        buffer.append(line)
    if buffer:
        sections.append({"heading": heading, "body": "\n".join(buffer).strip()})

    chunks: List[Dict[str, str]] = []
    for section in sections:
        text = section["body"] or section["heading"]
        while len(text) > max_chars:
            cut = text.rfind("\n\n", 0, max_chars) or max_chars
            chunks.append({"heading": section["heading"], "body": text[:cut].strip()})
            text = text[cut:].strip()
        if text:
            chunks.append({"heading": section["heading"], "body": text})
    return chunks


def ingest(
    conn: sqlite3.Connection,
    *,
    user_id: Optional[int],
    name: str,
    body: str,
    url: str = "",
    license: str = "unknown",
) -> Dict[str, Any]:
    name = (name or "").strip()[:200]
    if not name:
        raise ValueError("المصدر يحتاج اسم")
    chunks = split_chunks(body)
    if not chunks:
        raise ValueError("المصدر فارغ")
    license = (license or "unknown").strip().lower()
    if license not in KNOWN_LICENSES:
        raise ValueError(f"ترخيص غير معروف: {license}")

    cursor = conn.execute(
        """INSERT INTO rag_sources (user_id, name, license, url, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, name, license, url[:500], time.time()),
    )
    source_id = int(cursor.lastrowid)
    conn.executemany(
        """INSERT INTO rag_chunks (source_id, heading, body, created_at)
           VALUES (?, ?, ?, ?)""",
        [(source_id, chunk["heading"], chunk["body"], time.time()) for chunk in chunks],
    )
    return {"source_id": source_id, "name": name, "license": license, "chunks": len(chunks)}


def list_sources(conn: sqlite3.Connection, user_id: Optional[int]) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """SELECT s.*, (SELECT COUNT(*) FROM rag_chunks c WHERE c.source_id = s.id) AS chunks
             FROM rag_sources s
            WHERE s.user_id IS NULL OR s.user_id = ?
            ORDER BY s.id DESC""",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def delete_source(conn: sqlite3.Connection, user_id: Optional[int], source_id: int) -> bool:
    row = conn.execute("SELECT user_id FROM rag_sources WHERE id = ?", (source_id,)).fetchone()
    if row is None:
        return False
    if row["user_id"] not in (None, user_id):
        return False
    conn.execute("DELETE FROM rag_sources WHERE id = ?", (source_id,))
    return True


def search(
    conn: sqlite3.Connection, user_id: Optional[int], query: str, limit: int = 5
) -> List[Dict[str, Any]]:
    query_tokens = set(tokens(query))
    if not query_tokens:
        return []
    rows = conn.execute(
        """SELECT c.id, c.heading, c.body, s.name AS source, s.license, s.url, s.user_id
             FROM rag_chunks c JOIN rag_sources s ON s.id = c.source_id
            WHERE s.user_id IS NULL OR s.user_id = ?""",
        (user_id,),
    ).fetchall()

    scored: List[Dict[str, Any]] = []
    for row in rows:
        chunk_tokens = set(tokens(row["body"] + " " + row["heading"]))
        overlap = query_tokens & chunk_tokens
        if not overlap:
            continue
        score = len(overlap) / len(query_tokens)
        scored.append(
            {
                "chunk_id": row["id"],
                "source": row["source"],
                "license": row["license"],
                "url": row["url"],
                "heading": row["heading"],
                "body": row["body"],
                "score": round(score, 3),
                "citation": f"{row['source']}#{row['id']} ({row['license']})",
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[: max(1, min(limit, 20))]


def context_block(results: Iterable[Dict[str, Any]], max_chars: int = 4000) -> str:
    """Compact citation block to prepend to a prompt."""
    parts: List[str] = []
    used = 0
    for item in results:
        snippet = f"[{item['citation']}] {item['body']}"
        if used + len(snippet) > max_chars:
            break
        parts.append(snippet)
        used += len(snippet)
    return "\n\n".join(parts)


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)
