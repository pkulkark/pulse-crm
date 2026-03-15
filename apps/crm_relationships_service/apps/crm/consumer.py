import json
import logging
import os
import sys
import threading
import time

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from kafka import KafkaConsumer

from .models import Company, Task, TaskPriority


logger = logging.getLogger(__name__)

EVENT_TYPE = "deal.status_changed"
SUPPORTED_EVENT_VERSION = 1
QUALIFYING_STATUS = "QUALIFIED"
FOLLOW_UP_TITLE = "Schedule follow-up"
VALID_DEAL_STATUSES = {"NEW", "QUALIFIED", "WON", "LOST"}

_consumer_thread = None
_consumer_lock = threading.Lock()


def log_consumer_event(event, **fields):
    logger.info(json.dumps({"event": event, **fields}))


def validate_event_payload(payload):
    required_fields = (
        "eventId",
        "eventType",
        "eventVersion",
        "occurredAt",
        "dealId",
        "companyId",
        "oldStatus",
        "newStatus",
    )

    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required event fields: {', '.join(missing_fields)}.")

    if payload["eventType"] != EVENT_TYPE:
        raise ValueError(f"Unsupported event type: {payload['eventType']}.")

    if payload["eventVersion"] != SUPPORTED_EVENT_VERSION:
        raise ValueError(
            f"Unsupported event version: {payload['eventVersion']}.",
        )

    if payload["oldStatus"] not in VALID_DEAL_STATUSES:
        raise ValueError(f"Unsupported oldStatus value: {payload['oldStatus']}.")

    if payload["newStatus"] not in VALID_DEAL_STATUSES:
        raise ValueError(f"Unsupported newStatus value: {payload['newStatus']}.")


def process_deal_status_changed_event(payload):
    validate_event_payload(payload)

    if not Company.objects.filter(id=payload["companyId"]).exists():
        raise ValueError("Company not found for deal status event.")

    if payload["newStatus"] != QUALIFYING_STATUS:
        log_consumer_event(
            "deal_status_changed_no_action",
            outcome="no_action",
            eventId=payload["eventId"],
            dealId=payload["dealId"],
            companyId=payload["companyId"],
        )
        return {"outcome": "no_action", "taskId": None}

    with transaction.atomic():
        task, created = Task.objects.get_or_create(
            source_event_id=payload["eventId"],
            defaults={
                "title": FOLLOW_UP_TITLE,
                "company_id": payload["companyId"],
                "deal_id": payload["dealId"],
                "user_id": settings.ASYNC_TASK_DEFAULT_USER_ID,
                "priority": TaskPriority.MEDIUM,
            },
        )

    outcome = "task_created" if created else "duplicate_ignored"
    log_consumer_event(
        f"deal_status_changed_{outcome}",
        outcome=outcome,
        eventId=payload["eventId"],
        dealId=payload["dealId"],
        companyId=payload["companyId"],
        taskId=str(task.id),
    )

    return {"outcome": outcome, "taskId": str(task.id)}


def handle_consumer_message(message):
    payload = message.value
    log_consumer_event(
        "deal_status_changed_received",
        eventId=payload.get("eventId"),
        dealId=payload.get("dealId"),
        companyId=payload.get("companyId"),
        offset=message.offset,
        partition=message.partition,
        topic=message.topic,
    )

    return process_deal_status_changed_event(payload)


def build_consumer():
    return KafkaConsumer(
        settings.DEAL_STATUS_CHANGED_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=settings.KAFKA_CONSUMER_POLL_TIMEOUT_MS,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def run_consumer_loop():
    while True:
        consumer = None
        try:
            consumer = build_consumer()
            log_consumer_event(
                "deal_status_changed_consumer_started",
                startedAt=timezone.now().isoformat(),
                topic=settings.DEAL_STATUS_CHANGED_TOPIC,
                groupId=settings.KAFKA_CONSUMER_GROUP,
            )

            while True:
                records = consumer.poll(timeout_ms=settings.KAFKA_CONSUMER_POLL_TIMEOUT_MS)

                for message_batch in records.values():
                    for message in message_batch:
                        if process_message_with_retries(message):
                            consumer.commit()
        except Exception as exc:
            log_consumer_event(
                "deal_status_changed_consumer_error",
                error=str(exc),
                topic=settings.DEAL_STATUS_CHANGED_TOPIC,
            )
            time.sleep(settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS)
        finally:
            if consumer is not None:
                consumer.close()


def process_message_with_retries(message):
    for attempt in range(1, settings.KAFKA_CONSUMER_MAX_RETRIES + 1):
        try:
            handle_consumer_message(message)
            return True
        except ValueError as exc:
            log_consumer_event(
                "deal_status_changed_invalid_event",
                error=str(exc),
                eventId=message.value.get("eventId"),
                dealId=message.value.get("dealId"),
                companyId=message.value.get("companyId"),
            )
            return True
        except Exception as exc:
            if attempt == settings.KAFKA_CONSUMER_MAX_RETRIES:
                log_consumer_event(
                    "deal_status_changed_processing_failed",
                    attempt=attempt,
                    error=str(exc),
                    eventId=message.value.get("eventId"),
                    dealId=message.value.get("dealId"),
                    companyId=message.value.get("companyId"),
                )
                return False
            log_consumer_event(
                "deal_status_changed_retry_scheduled",
                attempt=attempt,
                error=str(exc),
                eventId=message.value.get("eventId"),
                dealId=message.value.get("dealId"),
                companyId=message.value.get("companyId"),
            )
            time.sleep(settings.KAFKA_CONSUMER_RETRY_DELAY_SECONDS)

    return False


def should_start_consumer():
    if not settings.KAFKA_CONSUMER_ENABLED:
        return False

    blocked_commands = {"check", "makemigrations", "migrate", "shell", "test"}
    if blocked_commands.intersection(sys.argv):
        return False

    if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return False

    return True


def start_consumer_thread():
    global _consumer_thread

    if not should_start_consumer():
        return

    with _consumer_lock:
        if _consumer_thread is not None and _consumer_thread.is_alive():
            return

        _consumer_thread = threading.Thread(
            target=run_consumer_loop,
            name="crm-deal-status-consumer",
            daemon=True,
        )
        _consumer_thread.start()
