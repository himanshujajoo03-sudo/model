"""
Kafka producer wrapper for the ingestion service.
Wraps confluent-kafka Producer to produce Canonical Weather Events.
"""

import os
import json
import logging

logger = logging.getLogger("ingestion.producer")


class KafkaProducer:
    """Wrapper around confluent-kafka Producer."""

    def __init__(self):
        bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        logger.info(f"Kafka producer initializing — bootstrap: {bootstrap}")
        # TODO: Initialize confluent_kafka.Producer
