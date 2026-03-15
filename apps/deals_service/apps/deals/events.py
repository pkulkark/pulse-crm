import json
import logging
import uuid
from datetime import timezone

from django.conf import settings
from kafka import KafkaProducer


logger = logging.getLogger(__name__)

EVENT_TYPE = "deal.status_changed"
EVENT_VERSION = 1


def format_utc_timestamp(value):
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_deal_status_changed_event(*, deal, old_status, new_status):
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": EVENT_TYPE,
        "eventVersion": EVENT_VERSION,
        "occurredAt": format_utc_timestamp(deal.updated_at),
        "dealId": str(deal.id),
        "companyId": str(deal.company_id),
        "oldStatus": old_status,
        "newStatus": new_status,
    }


def publish_deal_status_changed_event(event, *, correlation_id):
    producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        acks="all",
        retries=0,
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )

    try:
        result = producer.send(
            settings.DEAL_STATUS_CHANGED_TOPIC,
            key=event["eventId"],
            value=event,
        ).get(timeout=settings.KAFKA_PRODUCER_TIMEOUT_SECONDS)
        producer.flush(timeout=settings.KAFKA_PRODUCER_TIMEOUT_SECONDS)
    finally:
        producer.close()

    logger.info(
        json.dumps(
            {
                "event": "deal_status_changed_event_published",
                "correlationId": correlation_id,
                "eventId": event["eventId"],
                "dealId": event["dealId"],
                "companyId": event["companyId"],
                "partition": result.partition,
                "topic": result.topic,
            }
        )
    )


def emit_deal_status_changed_event(*, deal, old_status, new_status, correlation_id):
    event = build_deal_status_changed_event(
        deal=deal,
        old_status=old_status,
        new_status=new_status,
    )
    logger.info(
        json.dumps(
            {
                "event": "deal_status_changed_event_ready",
                "correlationId": correlation_id,
                "eventId": event["eventId"],
                "dealId": event["dealId"],
                "companyId": event["companyId"],
            }
        )
    )
    try:
        publish_deal_status_changed_event(
            event,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        logger.error(
            json.dumps(
                {
                    "event": "deal_status_changed_event_publish_failed",
                    "correlationId": correlation_id,
                    "eventId": event["eventId"],
                    "dealId": event["dealId"],
                    "companyId": event["companyId"],
                    "error": str(exc),
                }
            )
        )
