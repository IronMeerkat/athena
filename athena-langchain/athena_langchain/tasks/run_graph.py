"""
Celery task for executing LangChain graphs.

This module defines the ``run_graph`` task which is responsible for
selecting the correct agent/graph based on the provided manifest and
invoking it with the supplied input.  In this boilerplate the task
doesn't actually run any LangChain components; instead it logs the
inputs and returns a placeholder result.  Implement your own logic
here to instantiate and run LangChain graphs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

from ..manifest import CapabilityManifest
from ..config import Settings
from ..registry import PUBLIC_AGENTS, SENSITIVE_AGENTS
from ..agents import __init__ as _agents_imports  # noqa: F401  # ensure registration side-effects
from kombu import Connection, Exchange, Producer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@shared_task(bind=True, name="runs.execute_graph")
def run_graph(self, run_id: str, agent_id: str, payload: Any, manifest: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Execute a LangChain agent or graph based on the provided manifest.

    :param run_id: A unique identifier for this run, assigned by the
        gateway.  It can be used to correlate worker logs with API
        events.
    :param agent_id: The identifier of the agent to run.  This must be
        present in the appropriate registry given the queue specified in
        the manifest.
    :param payload: Arbitrary input to the agent.  This could be a
        dictionary containing user input, conversation state, etc.
    :param manifest: A JSON‑serializable dict describing the
        permissions and limits for this run.  If omitted, a default
        manifest will be assumed which grants no capabilities.
    :returns: A dict containing the result of the agent execution.  In
        this stub implementation a simple echo of the input is returned.
    """
    # Deserialize the manifest if provided; otherwise create a default
    # manifest with minimal permissions.  In a real application the
    # manifest should always be provided by the gateway to enforce
    # deterministic access to agents, tools and memory.
    cap = CapabilityManifest.from_dict(manifest or {})
    logger.info(
        "Running agent %s with run_id %s on queue %s", agent_id, run_id, cap.queue
    )

    # Ensure agent is registered
    # Select registry by queue
    registry = SENSITIVE_AGENTS if cap.queue == "sensitive" else PUBLIC_AGENTS
    try:
        entry = registry.get(agent_id)
    except KeyError:
        logger.error("Agent %s not found in registry for queue %s", agent_id, cap.queue)
        return {
            "status": "error",
            "message": f"Agent '{agent_id}' not found for queue '{cap.queue}'",
        }

    # Build the agent graph and run it
    settings = Settings()
    llm = registry.build_llm(settings, agent_id)
    graph = entry.build_graph(settings, llm)
    runnable = graph.compile()

    # Prepare RabbitMQ event publisher for streaming
    broker_url = settings.celery_broker_url if hasattr(settings, "celery_broker_url") else "amqp://admin:admin@rabbitmq:5672//"
    exchange = Exchange("runs", type="topic")
    routing_key = f"runs.{run_id}"

    def publish(event: str, data: Dict[str, Any]) -> None:
        try:
            with Connection(broker_url) as conn:
                with conn.channel() as channel:
                    producer = Producer(channel)
                    producer.publish({"event": event, "data": data}, exchange=exchange, routing_key=routing_key, serializer="json", declare=[exchange])
        except Exception:
            # Best-effort publishing; do not fail the run on stream errors
            pass


    try:
        result = runnable.invoke(payload)
        logger.info(f"result: {result}")
        result = result or True
        publish("run_completed", result)

        return {
            "status": "ok",
            "run_id": run_id,
            "agent_id": agent_id,
            "result": result,
            "ack": True,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Agent %s failed: %s", agent_id, e)
        publish("run_error", {"message": str(e)})
        return {"status": "error", "message": str(e)}
