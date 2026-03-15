# Phase 6: CRM Relationships Service, Part 2

## Objective

Add work tracking and relationship history to the CRM Relationships service.

## Scope

- `Task`
- `Activity`
- task list and update flows
- activity create and history flows
- support for async-created tasks in normal reads

## Engineering Standards

- code quality must be industry-standard and production-level
- keep the distinction between historical records and work items explicit
- do not overengineer task orchestration or timeline frameworks
- avoid overly defensive model design that adds fields or abstractions without a real product need
- keep attachment rules to company/contact/deal simple and validated

## Work Breakdown

1. Implement `Task` and `Activity` models and migrations.
2. Implement task queries and mutations.
3. Implement activity create and list queries.
4. Support filtering tasks by status, assignee, and due date.
5. Support activity association with company and optional contact/deal.
6. Make sure Kafka-generated tasks appear through the normal task APIs.
7. Add tests for task filtering and activity attachment rules.

## Deliverables

- task persistence and updates
- activity history persistence and retrieval
- shared CRM Relationships service APIs for company, contact, task, and activity data

## Acceptance Criteria

- task list works through the gateway
- a task can be updated from open to complete
- an activity can be logged against a company and optionally a contact or deal
- async-created tasks are visible through the same reads as manually created tasks

## Out of Scope

- activity participants
- reminders and notifications
- timeline aggregation beyond basic queries

## Recommended Verification

- manually create a task and an activity
- verify company and deal views can show related tasks and activities
- verify task filters return expected results

