"""Shared harness dataclasses for agent lifecycle scenario tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agi_procesor.agents.executor import AgentExecutor
from agi_procesor.agents.manager import AgentManager
from agi_procesor.agents.scheduler import AgentScheduler
from agi_procesor.core.events import EventBus
from tests.agents.fake_engine import FakeEngine


@dataclass(slots=True)
class FakeSystem:
    """Lightweight stand-in for AgiSystem — just engine + model."""

    engine: FakeEngine
    model: str = "fake-model"
    memory_backend: Any = None
    channel_backend: Any = None
    tools: list = field(default_factory=list)
    config: Any = None
    session_store: Any = None


@dataclass(slots=True)
class ScenarioHarness:
    """All components needed for an agent lifecycle scenario test."""

    manager: AgentManager
    executor: AgentExecutor
    scheduler: AgentScheduler
    bus: EventBus
    engine: FakeEngine
    system: FakeSystem
    db_path: str
