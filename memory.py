"""Simple embedding-based memory for past Q&A pairs."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in text.split() if len(w) > 2}


def _hash_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-words hash embedding (no external API needed)."""
    vec = [0.0] * dim
    for token in _tokenize(text):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class MemoryStore:
    """Stores past questions/answers with embeddings for retrieval."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path("results/memory.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")

    def add(self, question: str, answer: str, tools_used: list[str] | None = None) -> None:
        self.entries.append(
            {
                "question": question,
                "answer": answer,
                "tools_used": tools_used or [],
                "embedding": _hash_embed(question),
            }
        )
        self._save()

    def recall(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not self.entries:
            return []
        query_vec = _hash_embed(question)
        scored = []
        for entry in self.entries:
            sim = _cosine(query_vec, entry["embedding"])
            scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "question": e["question"],
                "answer": e["answer"],
                "tools_used": e.get("tools_used", []),
                "similarity": round(s, 3),
            }
            for s, e in scored[:top_k]
            if s > 0.1
        ]

    def format_context(self, question: str) -> str:
        recalls = self.recall(question)
        if not recalls:
            return ""
        lines = ["Relevant past analyses:"]
        for r in recalls:
            lines.append(f"- Q: {r['question']}")
            lines.append(f"  A: {r['answer'][:200]}")
        return "\n".join(lines)
