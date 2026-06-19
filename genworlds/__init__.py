"""GenWorlds - Collaborative AI Agent Framework.

GenWorlds provides an event-based communication framework for building
multi-agent systems with AI-driven autonomous agents.

Key modules:
    - simulation: WebSocket server, metrics, and configuration
    - agents: Abstract and concrete agent implementations
    - worlds: World types and entity management
    - events: Event and action definitions
    - objects: Interactive objects in simulations
"""

__version__ = "0.1.0"
__author__ = "YeagerAI"

from genworlds.simulation import Simulation
from genworlds.simulation.metrics import get_metrics
from genworlds.simulation.config import get_config

__all__ = [
    "Simulation",
    "get_metrics",
    "get_config",
    "__version__",
]