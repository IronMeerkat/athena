"""
Task package for Athena LangChain.

Celery will discover and register any tasks defined in modules within
this package.  The ``run_graph`` task in ``run_graph.py`` is the
primary entry point for executing a LangChain agent or graph.  You can
define additional tasks for housekeeping, scheduled jobs or other
services alongside it.
"""

# Expose run_graph at package level for convenience
from .run_graph import run_graph  # noqa: F401