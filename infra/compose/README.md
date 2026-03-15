# Compose Notes

Phase 0 keeps Compose intentionally small:

- one container per planned app/service
- one Postgres container per Django service
- one Kafka broker for later asynchronous phases

The services currently expose only placeholder responses and health endpoints.
