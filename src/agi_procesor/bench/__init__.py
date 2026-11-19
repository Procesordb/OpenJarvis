"""Benchmarking framework for AGI PROCESOR inference engines."""

from __future__ import annotations

from agi_procesor.bench._stubs import BaseBenchmark, BenchmarkResult, BenchmarkSuite
from agi_procesor.core.registry import BenchmarkRegistry


def ensure_registered() -> None:
    """Ensure all benchmark implementations are registered."""
    from agi_procesor.bench.energy import ensure_registered as _reg_energy
    from agi_procesor.bench.latency import ensure_registered as _reg_latency
    from agi_procesor.bench.throughput import ensure_registered as _reg_throughput

    _reg_latency()
    _reg_throughput()
    _reg_energy()


# Trigger registration on import
ensure_registered()

__all__ = [
    "BaseBenchmark",
    "BenchmarkRegistry",
    "BenchmarkResult",
    "BenchmarkSuite",
    "ensure_registered",
]
