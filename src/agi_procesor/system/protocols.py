"""Structural protocols for substituting fakes in place of AgiSystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Protocol

if TYPE_CHECKING:
    from agi_procesor.core.config import AgiConfig
    from agi_procesor.core.events import EventBus
    from agi_procesor.engine._stubs import InferenceEngine
    from agi_procesor.security.capabilities import CapabilityPolicy
    from agi_procesor.sessions.session import SessionStore
    from agi_procesor.tools._stubs import BaseTool
    from agi_procesor.tools.storage._stubs import MemoryBackend
    from agi_procesor.traces.collector import TraceCollector
    from agi_procesor.traces.store import TraceStore


class OrchestratorDeps(Protocol):
    """Minimum surface of AgiSystem that QueryOrchestrator depends on.

    Tests can satisfy this with a lightweight class — no need to construct
    the full AgiSystem dataclass or materialize every subsystem.
    """

    config: AgiConfig
    bus: EventBus
    engine: InferenceEngine
    engine_key: str
    model: str
    agent_name: str
    tools: List[BaseTool]
    memory_backend: Optional[MemoryBackend]
    capability_policy: Optional[CapabilityPolicy]
    rate_limiter: Optional[Any]
    session_store: Optional[SessionStore]
    trace_store: Optional[TraceStore]
    trace_collector: Optional[TraceCollector]  # written by _run_agent

    # Optional attribute (getattr with default) — declared for type clarity.
    _skill_few_shot_examples: Any
