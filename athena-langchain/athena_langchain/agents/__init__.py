"""
Import agent modules for registration side effects.
"""

# Ensure agents are registered when this package is imported
from . import anti_distraction_agent  # noqa: F401
from . import appeals_agent  # noqa: F401
from . import goals_scheduler_agent  # noqa: F401
from . import distraction_guardian  # noqa: F401

"""
Package for agent implementations.

Define your LangChain agents in this package.  Agents can be simple
functions, LangChain chains or more complex graphs defined using
LangGraph.  Registries reference the callables defined here.
"""

__all__: list[str] = []