#!/usr/bin/env python3
"""
RabbitMQ Connection Health Monitor
Run this periodically to check connection stability
"""
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_rabbitmq_health():
    """Check RabbitMQ server health and connections"""
    try:
        # Check overall health
        health_response = requests.get(
            'http://localhost:15672/api/healthchecks/node',
            auth=('admin', 'admin'),
            timeout=10
        )

        # Check connections
        connections_response = requests.get(
            'http://localhost:15672/api/connections',
            auth=('admin', 'admin'),
            timeout=10
        )

        # Check queues
        queues_response = requests.get(
            'http://localhost:15672/api/queues',
            auth=('admin', 'admin'),
            timeout=10
        )

        if health_response.status_code == 200:
            logger.info("✅ RabbitMQ health check passed")
        else:
            logger.warning(f"⚠️ RabbitMQ health check failed: {health_response.status_code}")

        if connections_response.status_code == 200:
            connections = connections_response.json()
            active_connections = [c for c in connections if c['state'] == 'running']
            logger.info(f"📊 Active connections: {len(active_connections)}")

            for conn in active_connections:
                logger.info(f"   • {conn['user']}@{conn['peer_host']} (state: {conn['state']})")

        if queues_response.status_code == 200:
            queues = queues_response.json()
            total_messages = sum(q.get('messages', 0) for q in queues)
            logger.info(f"📨 Total queued messages: {total_messages}")

            for queue in queues:
                if queue.get('messages', 0) > 0:
                    logger.info(f"   • Queue '{queue['name']}': {queue['messages']} messages")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to connect to RabbitMQ management API: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print(f"🔍 RabbitMQ Health Check - {datetime.now()}")
    check_rabbitmq_health()
