"""Native persistent long-term memory for AGI PROCESOR.

This package provides the automatic memory service that extracts durable facts
from conversations in the background and persists them across sessions. It is
started and stopped as part of the ``agi serve`` / ``agi chat`` lifecycle
and configured via the ``[memory]`` section of ``config.toml``.
"""

from __future__ import annotations

from agi_procesor.memory.extractor import FactExtractor
from agi_procesor.memory.service import (
    MemoryService,
    build_memory_service,
    publish_completed_exchange,
)
from agi_procesor.memory.store import (
    Fact,
    FactStore,
    LocalFactStore,
    create_fact_store,
    load_configured_facts,
)

__all__ = [
    "Fact",
    "FactStore",
    "FactExtractor",
    "LocalFactStore",
    "MemoryService",
    "build_memory_service",
    "create_fact_store",
    "load_configured_facts",
    "publish_completed_exchange",
]
