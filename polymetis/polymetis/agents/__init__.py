"""
Import agent modules for registration side effects.
"""

# Ensure agents are registered when this package is imported
from . import appeals_agent  # noqa: F401
from . import goals_scheduler_agent  # noqa: F401
from . import guardian  # noqa: F401
from . import journaling_agent  # noqa: F401
from . import mongo_query_agent  # noqa: F401
from . import interviewer_agent  # noqa: F401

__all__: list[str] = []
