"""Tracing helpers.

LocalTracer records span timings in-memory and assembles the TraceSummary the
telemetry panel consumes — the exact same summary shape the Azure tracer produces,
so the frontend Gantt works identically in both runtimes. The Azure tracer
(shared/tracing_azure.py, Phase 5) subclasses this and also exports OTel spans to
Azure Monitor.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from shared.interfaces.tracer import Span, Tracer
from shared.state_schema import SpanSummary, TraceSummary


class _LocalSpan(Span):
    def __init__(self, name: str):
        self.name = name
        self.attributes: dict = {}

    def set_attribute(self, key: str, value) -> None:
        self.attributes[key] = value


class LocalTracer(Tracer):
    def __init__(self):
        self._records: list[tuple[str, int]] = []  # (name, ms)
        self._turn_start = time.perf_counter()

    @contextmanager
    def span(self, name: str) -> Iterator[Span]:
        sp = _LocalSpan(name)
        start = time.perf_counter()
        try:
            yield sp
        finally:
            self._records.append((name, int((time.perf_counter() - start) * 1000)))

    def build_summary(
        self, turn: int, trace_id: str, agent_messages: dict[str, str]
    ) -> TraceSummary:
        total = int((time.perf_counter() - self._turn_start) * 1000)
        summary = TraceSummary(
            turn=turn,
            trace_id=trace_id,
            total_ms=total,
            spans=[SpanSummary(name=n, ms=ms) for n, ms in self._records],
            agent_messages=agent_messages,
        )
        # reset for next turn
        self._records = []
        self._turn_start = time.perf_counter()
        return summary
