from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterator

from shared.state_schema import TraceSummary


class Span(ABC):
    @abstractmethod
    def set_attribute(self, key: str, value) -> None: ...


class Tracer(ABC):
    """Produces OpenTelemetry spans AND a mode-independent TraceSummary for the
    telemetry panel. The local tracer records timings in-memory; the azure tracer
    additionally exports to Azure Monitor. The summary shape is identical either way."""

    @abstractmethod
    @contextmanager
    def span(self, name: str) -> Iterator[Span]: ...

    @abstractmethod
    def build_summary(self, turn: int, trace_id: str, agent_messages: dict[str, str]) -> TraceSummary:
        """Assemble the per-turn summary from recorded spans, then reset for next turn."""
