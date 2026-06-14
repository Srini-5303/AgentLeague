"""Local KnowledgeStore: keyword search over the knowledge/*.md world bible.

Chunks each markdown doc by its `## Section` headings. A chunk is flagged gm_only
if its heading is a secrets section or its text contains the `[GM ONLY]` marker —
these are filtered out unless include_secrets=True (the GM/narrator path). This is
the local stand-in for Foundry IQ; the same markdown files later feed the Foundry
IQ index, so retrieval behavior is comparable.
"""
from __future__ import annotations

import re
from pathlib import Path

from shared.interfaces.knowledge import KnowledgeStore, LoreChunk

_WORD = re.compile(r"[a-z0-9]+")
_GM_MARKER = "[gm only]"
_SECRET_HEADINGS = {"secrets", "gm notes", "gm only"}


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class LocalKnowledgeStore(KnowledgeStore):
    def __init__(self, knowledge_dir: str):
        self._dir = Path(knowledge_dir)
        self._chunks: list[LoreChunk] = []
        self._index: list[set[str]] = []
        self._load()

    def _load(self) -> None:
        if not self._dir.exists():
            return
        for path in sorted(self._dir.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            entity = self._first_h1(raw) or path.stem
            for heading, body in self._sections(raw):
                gm_only = (heading.strip().lower() in _SECRET_HEADINGS) or (
                    _GM_MARKER in body.lower()
                )
                self._chunks.append(
                    LoreChunk(
                        source=path.name,
                        title=f"{entity} — {heading}" if heading else entity,
                        text=body.strip(),
                        gm_only=gm_only,
                    )
                )
        self._index = [_tokens(c.title + " " + c.text) for c in self._chunks]

    @staticmethod
    def _first_h1(raw: str) -> str | None:
        m = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _sections(raw: str) -> list[tuple[str, str]]:
        # Split on level-2 headings; keep preamble under "" heading.
        parts = re.split(r"^##\s+(.+)$", raw, flags=re.MULTILINE)
        out: list[tuple[str, str]] = []
        if parts[0].strip():
            out.append(("Overview", parts[0]))
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            out.append((heading, body))
        return out

    async def search(
        self, query: str, *, top_k: int = 3, include_secrets: bool = False
    ) -> list[LoreChunk]:
        q = _tokens(query)
        scored: list[LoreChunk] = []
        for chunk, toks in zip(self._chunks, self._index):
            if chunk.gm_only and not include_secrets:
                continue
            overlap = len(q & toks)
            if overlap:
                c = chunk.model_copy()
                c.score = overlap / (len(q) or 1)
                scored.append(c)
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]
