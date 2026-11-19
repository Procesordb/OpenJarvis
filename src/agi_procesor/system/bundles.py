"""Bundle dataclasses that group cohesive subsystems of AgiSystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from agi_procesor.agents._stubs import BaseAgent
    from agi_procesor.agents.executor import AgentExecutor
    from agi_procesor.agents.manager import AgentManager
    from agi_procesor.agents.scheduler import AgentScheduler
    from agi_procesor.scheduler.scheduler import TaskScheduler
    from agi_procesor.scheduler.store import SchedulerStore
    from agi_procesor.security.audit import AuditLogger
    from agi_procesor.security.boundary import BoundaryGuard
    from agi_procesor.security.capabilities import CapabilityPolicy
    from agi_procesor.telemetry.gpu_monitor import GpuMonitor
    from agi_procesor.telemetry.store import TelemetryStore
    from agi_procesor.traces.collector import TraceCollector
    from agi_procesor.traces.store import TraceStore


@dataclass
class SecurityContext:
    """Security policy, audit, and boundary enforcement."""

    capability_policy: Optional[CapabilityPolicy] = None
    audit_logger: Optional[AuditLogger] = None
    boundary_guard: Optional[BoundaryGuard] = None
    rate_limiter: Optional[Any] = None


@dataclass
class Observability:
    """Telemetry, traces, and hardware monitoring."""

    telemetry_store: Optional[TelemetryStore] = None
    trace_store: Optional[TraceStore] = None
    trace_collector: Optional[TraceCollector] = None
    gpu_monitor: Optional[GpuMonitor] = None


@dataclass
class AgentRuntime:
    """Active agent and agent lifecycle managers."""

    agent: Optional[BaseAgent] = None
    agent_name: str = ""
    manager: Optional[AgentManager] = None
    scheduler: Optional[AgentScheduler] = None
    executor: Optional[AgentExecutor] = None


@dataclass
class Scheduling:
    """Task scheduler and its persistent store."""

    store: Optional[SchedulerStore] = None
    runner: Optional[TaskScheduler] = None
