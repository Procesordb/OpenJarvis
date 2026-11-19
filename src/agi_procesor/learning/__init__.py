"""Learning primitive -- router policies, reward functions, learning."""

from __future__ import annotations

from agi_procesor.learning._stubs import (
    QueryAnalyzer,
    RewardFunction,
    RouterPolicy,
    RoutingContext,
)
from agi_procesor.learning.agents.agent_evolver import AgentConfigEvolver
from agi_procesor.learning.learning_orchestrator import LearningOrchestrator
from agi_procesor.learning.optimize.llm_optimizer import LLMOptimizer
from agi_procesor.learning.optimize.optimizer import OptimizationEngine
from agi_procesor.learning.optimize.store import OptimizationStore
from agi_procesor.learning.routing.complexity import (
    ComplexityQueryAnalyzer,
    score_complexity,
)
from agi_procesor.learning.routing.heuristic_reward import HeuristicRewardFunction
from agi_procesor.learning.routing.router import (
    HeuristicRouter,
    build_routing_context,
)
from agi_procesor.learning.training.data import TrainingDataMiner
from agi_procesor.learning.training.lora import (
    HAS_TORCH,
    LoRATrainer,
    LoRATrainingConfig,
)


def ensure_registered() -> None:
    """Ensure all learning policies are registered in RouterPolicyRegistry."""
    from agi_procesor.learning.routing.heuristic_policy import (
        ensure_registered as _reg_heuristic,
    )

    _reg_heuristic()

    from agi_procesor.learning.routing.learned_router import (
        ensure_registered as _reg_learned,
    )

    _reg_learned()

    # Intelligence training (optional deps)
    try:
        import agi_procesor.learning.intelligence  # noqa: F401
    except ImportError:
        pass

    # Orchestrator-specific training (optional deps)
    try:
        import agi_procesor.learning.intelligence.orchestrator  # noqa: F401
    except ImportError:
        pass

    # Agent optimizers (optional deps)
    try:
        import agi_procesor.learning.agents.dspy_optimizer  # noqa: F401
    except ImportError:
        pass
    try:
        import agi_procesor.learning.agents.gepa_optimizer  # noqa: F401
    except ImportError:
        pass
    try:
        import agi_procesor.learning.agents.ace_optimizer  # noqa: F401
    except ImportError:
        pass


__all__ = [
    "AgentConfigEvolver",
    "ComplexityQueryAnalyzer",
    "HAS_TORCH",
    "HeuristicRewardFunction",
    "HeuristicRouter",
    "LLMOptimizer",
    "LearningOrchestrator",
    "LoRATrainer",
    "LoRATrainingConfig",
    "OptimizationEngine",
    "OptimizationStore",
    "QueryAnalyzer",
    "RewardFunction",
    "RouterPolicy",
    "RoutingContext",
    "TrainingDataMiner",
    "build_routing_context",
    "ensure_registered",
    "score_complexity",
]
