"""Populate the Foundry IQ / Azure AI Search index from knowledge/*.md.

Reuses the LOCAL chunker so chunking + GM-only detection match the local store
exactly (same `[GM ONLY]` / Secrets rule), keeping retrieval behavior consistent
across runtimes. Run once after creating the AI Search index.

Index schema expected (create in portal or via azure-search-documents SDK):
  id (key, string) · title (string, searchable) · content (string, searchable)
  · source (string, filterable) · gm_only (bool, filterable)

Usage:
  pip install -r requirements-azure.txt
  python infra/upload_knowledge.py --endpoint https://<search>.search.windows.net --index eldervale-campaign
"""
from __future__ import annotations

import argparse
import hashlib

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from shared.knowledge.local_store import LocalKnowledgeStore


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--index", default="eldervale-campaign")
    ap.add_argument("--knowledge-dir", default="knowledge")
    args = ap.parse_args()

    store = LocalKnowledgeStore(args.knowledge_dir)
    docs = []
    for c in store._chunks:  # reuse the local chunking/secret detection
        docs.append({
            "id": hashlib.sha256(f"{c.source}:{c.title}".encode()).hexdigest()[:32],
            "title": c.title,
            "content": c.text,
            "source": c.source,
            "gm_only": c.gm_only,
        })

    client = SearchClient(args.endpoint, args.index, DefaultAzureCredential())
    result = client.upload_documents(documents=docs)
    ok = sum(1 for r in result if r.succeeded)
    print(f"uploaded {ok}/{len(docs)} chunks to index '{args.index}' "
          f"({sum(d['gm_only'] for d in docs)} GM-only)")


if __name__ == "__main__":
    main()
