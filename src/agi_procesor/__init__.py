"""AGI PROCESOR — modular AI assistant backend.

Built from composable intelligence primitives.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agi_procesor.sdk import AgiProcesor, AgiSystem, MemoryHandle, SystemBuilder

try:
    __version__ = _pkg_version("agi_procesor")
except PackageNotFoundError:  # pragma: no cover — uninstalled source tree
    __version__ = "0.0.0+unknown"

__all__ = ["AgiProcesor", "AgiSystem", "MemoryHandle", "SystemBuilder", "__version__"]

_SDK_EXPORTS = {"AgiProcesor", "AgiSystem", "MemoryHandle", "SystemBuilder"}


def __getattr__(name: str) -> Any:
    """Load SDK exports lazily so lightweight CLI diagnostics can start safely."""
    if name not in _SDK_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from agi_procesor import sdk

    value = getattr(sdk, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | _SDK_EXPORTS)
