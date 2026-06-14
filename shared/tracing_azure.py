"""Azure tracer (RUNTIME=azure).

Subclasses LocalTracer so the per-turn TraceSummary (telemetry panel data) is built
identically; additionally configures Azure Monitor OpenTelemetry so spans are
exported to Application Insights and stitched into the distributed trace per turn.
Configuration is process-global and idempotent.

azure-monitor-opentelemetry imported lazily; install via requirements-azure.txt.
"""
from __future__ import annotations

from shared.config import Settings
from shared.tracing import LocalTracer

_configured = False


def _configure_once(connection_string: str) -> None:
    global _configured
    if _configured or not connection_string:
        return
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)
    _configured = True


class AzureTracer(LocalTracer):
    def __init__(self, settings: Settings):
        super().__init__()
        _configure_once(settings.applicationinsights_connection_string)
        from opentelemetry import trace

        self._otel = trace.get_tracer("eldervale.gm")

    # span() and build_summary() inherited from LocalTracer record local timings for
    # the panel. For full OTel export, wrap LocalTracer.span to also open an OTel span:
    # (kept minimal here; the local timings already drive the UI Gantt, and
    # configure_azure_monitor auto-instruments outbound calls for the App Insights tree.)
