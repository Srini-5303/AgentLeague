"""Abstract interfaces — the seam between game logic and external services.

Each has a `local` and an `azure` implementation, selected by RUNTIME in
shared/factory.py. Game logic depends only on these ABCs, never on a concrete
service, which is what makes the local→Azure swap config-only.
"""
from shared.interfaces.auth import AuthProvider
from shared.interfaces.knowledge import KnowledgeStore, LoreChunk
from shared.interfaces.llm import LLMClient, LLMMessage
from shared.interfaces.state import StateStore
from shared.interfaces.tracer import Span, Tracer

__all__ = [
    "AuthProvider",
    "KnowledgeStore",
    "LoreChunk",
    "LLMClient",
    "LLMMessage",
    "StateStore",
    "Span",
    "Tracer",
]
