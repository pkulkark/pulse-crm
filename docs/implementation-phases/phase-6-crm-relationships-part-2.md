# Phase 6: CRM Relationships Service, Part 2

## Objective

Add work tracking and relationship history to the CRM Relationships service.

## Scope

- `Task`
- `Activity`
- task list and update flows
- activity create and history flows
- support for async-created tasks in normal reads

## API Contract

Use the phase-specific contract in [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md).

The implementation should follow that contract unless a clear technical reason requires a small adjustment. If the contract changes, update the contract doc in the same phase.

## Engineering Standards

- code quality must be industry-standard and production-level
- keep the distinction between historical records and work items explicit
- do not overengineer task orchestration or timeline frameworks
- avoid overly defensive model design that adds fields or abstractions without a real product need
- keep attachment rules to company/contact/deal simple and validated

## Work Breakdown

1. Confirm and implement the API contract for task and activity reads/writes.
2. Implement `Task` and `Activity` models and migrations.
3. Implement task queries and mutations.
4. Implement activity create and list queries.
5. Support filtering tasks by status, assignee, and due date.
6. Support activity association with company and optional contact/deal.
7. Make sure Kafka-generated tasks appear through the normal task APIs.
8. Add tests for task filtering and activity attachment rules.

## Deliverables

- task persistence and updates
- activity history persistence and retrieval
- shared CRM Relationships service APIs for company, contact, task, and activity data
- phase-specific API contract documented and implemented

## Acceptance Criteria

- task list works through the gateway
- a task can be updated from open to complete
- an activity can be logged against a company and optionally a contact or deal
- async-created tasks are visible through the same reads as manually created tasks
- implemented schema matches the documented Phase 6 contract, or any deviation is documented

## Out of Scope

- activity participants
- reminders and notifications
- timeline aggregation beyond basic queries

## Recommended Verification

- manually create a task and an activity
- verify company and deal views can show related tasks and activities
- verify task filters return expected results
