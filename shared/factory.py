"""The seam wiring: build concrete implementations from Settings.

Game logic calls these factories and receives interface types — it never imports a
concrete store/client/provider. Flipping RUNTIME (and provider env vars) is the
only change needed to move local→Azure. Azure modules are imported lazily so local
dev doesn't require the azure-* packages.
"""
from __future__ import annotations

from shared.config import Settings, get_settings
from shared.interfaces import AuthProvider, KnowledgeStore, LLMClient, StateStore, Tracer


def build_llm(settings: Settings | None = None) -> LLMClient:
    s = settings or get_settings()
    if s.runtime == "azure":
        from shared.llm.foundry_client import FoundryLLMClient
        return FoundryLLMClient(s)
    if s.llm_provider == "mock":
        from shared.llm.mock_client import MockLLMClient
        return MockLLMClient()
    from shared.llm.openai_client import OpenAICompatClient
    return OpenAICompatClient(s)


def build_knowledge(settings: Settings | None = None) -> KnowledgeStore:
    s = settings or get_settings()
    if s.runtime == "azure":
        from shared.knowledge.foundry_iq_store import FoundryIQStore
        return FoundryIQStore(s)
    from shared.knowledge.local_store import LocalKnowledgeStore
    return LocalKnowledgeStore(s.knowledge_dir)


def build_state(settings: Settings | None = None) -> StateStore:
    s = settings or get_settings()
    if s.runtime == "azure":
        from shared.state.cosmos_store import CosmosStateStore
        return CosmosStateStore(s)
    from shared.state.sqlite_store import SQLiteStateStore
    return SQLiteStateStore(s.sqlite_path)


def build_auth(settings: Settings | None = None) -> AuthProvider:
    s = settings or get_settings()
    if s.runtime == "azure":
        from shared.auth.entra_auth import EntraAuthProvider
        return EntraAuthProvider(s)
    from shared.auth.dev_auth import DevAuthProvider
    return DevAuthProvider(s)


def build_tracer(settings: Settings | None = None) -> Tracer:
    s = settings or get_settings()
    if s.runtime == "azure":
        from shared.tracing_azure import AzureTracer
        return AzureTracer(s)
    from shared.tracing import LocalTracer
    return LocalTracer()
