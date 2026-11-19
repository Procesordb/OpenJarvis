"""External-framework subprocess backends (Hermes Agent, OpenClaw)."""

from agi_procesor.evals.backends.external.hermes_agent import HermesBackend
from agi_procesor.evals.backends.external.openclaw import OpenClawBackend

__all__ = ["HermesBackend", "OpenClawBackend"]
