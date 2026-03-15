# Phase 5 Event Contract: `deal.status_changed`

## Purpose

This document defines the minimum event contract for Phase 5.

The goal is to support:

- publishing an event when a deal status changes
- consuming that event in the CRM Relationships service
- creating follow-up tasks asynchronously
- handling duplicate delivery safely

This is an event contract, not a GraphQL API contract.

## Contract Principles

- keep the payload minimal
- include enough data for the consumer to act without guessing
- make the event versionable
- make duplicate handling possible
- keep the producer and consumer loosely coupled

## Ownership

Producer:

- `Deals` service

Consumer:

- `CRM Relationships` service

## Topic

```text
deal.status_changed
```

## Event Schema

```json
{
  "eventId": "evt_123",
  "eventType": "deal.status_changed",
  "eventVersion": 1,
  "occurredAt": "2026-03-15T15:30:00Z",
  "dealId": "deal_42",
  "companyId": "company_10",
  "oldStatus": "NEW",
  "newStatus": "QUALIFIED"
}
```

## Field Definitions

- `eventId`
  - unique identifier for this event instance
  - used for deduplication

- `eventType`
  - fixed value: `deal.status_changed`

- `eventVersion`
  - schema version for forward evolution

- `occurredAt`
  - UTC timestamp for when the status change occurred

- `dealId`
  - identifier of the changed deal

- `companyId`
  - owning company of the deal

- `oldStatus`
  - previous deal status

- `newStatus`
  - updated deal status

## Producer Rules

- publish only after the deal status update succeeds
- emit one event per successful status change
- populate `oldStatus` and `newStatus` from persisted state transition logic
- generate a unique `eventId` for each emitted event

## Consumer Rules

- consume `deal.status_changed`
- determine whether the new status requires follow-up work
- create one or more `Task` records when required
- record enough metadata to avoid duplicate task creation for the same event

## Expected Side Effect

For the initial workflow, a status change such as:

- `NEW -> QUALIFIED`

may create a task such as:

- `Schedule follow-up`

The exact task title can be implementation-specific, but the mapping from `newStatus` to follow-up action should be explicit and testable.

## Idempotency Expectations

- the consumer must treat `eventId` as the primary deduplication key
- replaying the same event must not create duplicate tasks
- duplicate handling should be visible in logs

## Retry Expectations

- transient consumer failures may be retried
- retries must not change the idempotency guarantee
- failures should be logged with enough context to trace the event

## Validation Expectations

- `eventType` must match the expected topic semantics
- `eventVersion` must be supported
- `dealId`, `companyId`, `oldStatus`, and `newStatus` are required
- `oldStatus` and `newStatus` should be valid `DealStatus` enum values

## Example Task-Creation Rule

Example rule for the initial implementation:

- if `newStatus == QUALIFIED`, create a follow-up task for the company/deal
- otherwise, do nothing unless another rule is explicitly implemented

This keeps the initial workflow small and easy to verify.

## Observability Notes

Logs should include:

- `eventId`
- `dealId`
- `companyId`
- consumer outcome such as `task_created`, `no_action`, or `duplicate_ignored`

## Implementation Notes

- later phases may extend the mapping from status transitions to task rules without changing this event schema
- if the implementation chooses snake_case field names at the transport level, document that deviation here and keep the producer and consumer aligned

