"""
Athena LangChain package.

This package contains the components required to build and run LangChain
graphs for the Athena assistant.  It includes a Celery app used by
workers, task definitions, agent/tool registries and a capability
manifest definition.  Extend this package to include your own agents,
tools and memory backends.
"""

from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)