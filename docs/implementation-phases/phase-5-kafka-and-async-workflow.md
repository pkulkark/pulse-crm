# Phase 5: Kafka and Asynchronous Workflow

## Objective

Implement the core asynchronous workflow: a deal status change publishes an event that later creates follow-up tasks.

## Scope

- Kafka wiring in Docker Compose
- `deal.status_changed` topic and payload
- producer in `Deals`
- consumer in `CRM Relationships`
- idempotent task creation behavior

## Engineering Standards

- code quality must be industry-standard and production-level
- keep the event contract minimal and versionable
- do not overengineer the event topology; one topic and one clear consumer path is enough at this stage
- avoid overly defensive retry logic that hides failures; bounded retries and visible logs are preferable
- prioritize idempotency, traceability, and debuggability

## Work Breakdown

1. Add Kafka and required topics to Docker Compose.
2. Define the event payload contract.
3. Publish `deal.status_changed` from the `Deals` service after successful status updates.
4. Implement a consumer in `CRM Relationships`.
5. Create follow-up tasks based on the new status.
6. Add idempotency handling using `event_id` or equivalent deduplication key.
7. Add logs and metrics hooks around publish and consume paths.
8. Add tests for event publication and duplicate handling.

## Deliverables

- end-to-end asynchronous task creation
- visible eventual consistency path
- bounded retry and deduplication behavior

## Acceptance Criteria

- updating deal status publishes an event
- consumer receives the event and creates the expected task
- duplicate delivery does not create duplicate tasks
- logs are sufficient to trace a request from mutation to task creation

## Out of Scope

- full outbox pattern
- dead-letter queue automation
- multiple async workflows

## Recommended Verification

- update a deal status and inspect logs across services
- verify task creation through API or DB
- replay the same event and verify no duplicate task is created

