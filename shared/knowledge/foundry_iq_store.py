"""Foundry IQ knowledge store (RUNTIME=azure).

Foundry IQ is Microsoft's managed knowledge layer built over Azure AI Search, so we
query the underlying AI Search index directly (robust, GA surface) and map hits to
LoreChunk. The index is expected to carry per-chunk fields: title, content, source,
gm_only (bool). GM-only chunks are filtered server-side unless include_secrets=True.

Populate the index from knowledge/*.md with infra/upload_knowledge.py (chunks by
section, sets gm_only from the `[GM ONLY]` marker / Secrets heading) — the same
secret-detection rule as the local store, so behavior matches across runtimes.

azure-search-documents / azure-identity imported lazily; install via requirements-azure.txt.
"""
from __future__ import annotations

from shared.config import Settings
from shared.interfaces.knowledge import KnowledgeStore, LoreChunk


class FoundryIQStore(KnowledgeStore):
    def __init__(self, settings: Settings):
        from azure.identity.aio import DefaultAzureCredential
        from azure.search.documents.aio import SearchClient

        self._s = settings
        endpoint = settings.foundry_project_endpoint  # or a dedicated AI Search endpoint env
        self._credential = DefaultAzureCredential()
        self._client = SearchClient(
            endpoint=endpoint, index_name=settings.foundry_iq_index, credential=self._credential
        )

    async def search(
        self, query: str, *, top_k: int = 3, include_secrets: bool = False
    ) -> list[LoreChunk]:
        flt = None if include_secrets else "gm_only eq false"
        results = await self._client.search(search_text=query, top=top_k, filter=flt)
        chunks: list[LoreChunk] = []
        async for r in results:
            chunks.append(
                LoreChunk(
                    source=r.get("source", ""),
                    title=r.get("title", ""),
                    text=r.get("content", ""),
                    score=r.get("@search.score", 0.0),
                    gm_only=bool(r.get("gm_only", False)),
                )
            )
        return chunks
