# CRM Implementation Plan

## 1. Purpose

This document translates the architecture in [`architecture.md`](architecture.md) into a practical implementation plan.

The goal is to deliver a working system that:

- matches the required multi-service architecture
- demonstrates GraphQL federation clearly
- includes one meaningful Kafka-based asynchronous workflow
- remains small enough to finish with high quality

This plan follows a production-minded approach while staying realistic for an initial implementation.

Detailed implementation documents for each phase live in [`implementation-phases/README.md`](implementation-phases/README.md).

## 2. Delivery Strategy

The system should be implemented as a sequence of vertical slices rather than as isolated infrastructure or isolated CRUD screens.

Guiding principles:

- code quality must be industry-standard and production-level throughout the implementation
- do not overengineer; prefer simple, explicit solutions that match the current scope
- avoid overly defensive coding that obscures the main logic or duplicates checks without clear ownership
- prove the architecture early with the smallest end-to-end path
- add services only when their ownership boundary is clear
- keep every phase runnable in Docker Compose
- prefer a thin working slice over partially built broad scope
- add tests alongside critical business logic, not only at the end

## 3. Target End State

By the end of implementation, the system should support:

- login for internal users
- company creation and editing by admin users
- contact creation and editing by admin users
- deal creation and deal status updates
- activity logging
- task viewing and task updates
- a Kafka flow where a deal status change asynchronously creates follow-up tasks
- frontend access only through the GraphQL gateway
- server-side authorization across backend services

## 4. Recommended Build Order

The recommended sequence is:

1. Monorepo and local runtime foundation
2. GraphQL gateway skeleton
3. Identity/Access service
4. CRM Relationships service with `Company` and `Contact`
5. Deals service
6. Kafka integration and asynchronous task creation
7. CRM Relationships extension with `Task` and `Activity`
8. React frontend screens
9. Cross-service authorization hardening
10. Testing, docs, and operational polish

This order reduces risk because it proves the hardest architectural requirements before the UI surface becomes large.

## 5. Phased Plan

This document is the roadmap summary. The detailed execution plan for each phase is documented separately:

- [Phase 0: Repository and Workspace Setup](implementation-phases/phase-0-repository-and-workspace-setup.md)
- [Phase 1: GraphQL Gateway Skeleton](implementation-phases/phase-1-graphql-gateway-skeleton.md)
- [Phase 2: Identity and Access Service](implementation-phases/phase-2-identity-and-access-service.md)
- [Phase 3: CRM Relationships Service, Part 1](implementation-phases/phase-3-crm-relationships-part-1.md)
- [Phase 4: Deals Service](implementation-phases/phase-4-deals-service.md)
- [Phase 5: Kafka and Asynchronous Workflow](implementation-phases/phase-5-kafka-and-async-workflow.md)
- [Phase 6: CRM Relationships Service, Part 2](implementation-phases/phase-6-crm-relationships-part-2.md)
- [Phase 7: Frontend Screens](implementation-phases/phase-7-frontend-screens.md)
- [Phase 8: Authorization Hardening](implementation-phases/phase-8-authorization-hardening.md)
- [Phase 9: Quality, Documentation, and Release Finish](implementation-phases/phase-9-quality-documentation-and-release-finish.md)

## 6. Minimal End-to-End Milestone

Before expanding the full UI, the first major milestone should prove the architecture with the smallest meaningful slice.

Recommended milestone:

- login works
- admin can create a company
- user can create a deal for that company
- user can update deal status
- Kafka event is published
- follow-up task is created asynchronously
- task can be queried through the gateway

If this milestone works, the most important architectural risk is already retired.

## 7. Entity-to-Service Mapping

### Identity/Access Service

- `User`

### CRM Relationships Service

- `Company`
- `Contact`
- `Task`
- `Activity`

### Deals Service

- `Deal`

This mapping should remain stable unless a strong implementation reason emerges to change it.

## 8. Key Technical Decisions

### Authentication

Choose the simplest secure authentication approach that can be explained clearly. The important part is:

- authenticated users exist
- role information is available server-side
- downstream services do not trust raw frontend claims

### Database Strategy

- one database per service
- no direct reads across service databases
- use IDs and GraphQL federation for read composition

### Monorepo Strategy

- use `Nx` only as the workspace/task orchestration layer required by the specification
- keep each backend service as a plain Django project rather than forcing Django into a non-idiomatic Nx-native structure
- use Docker Compose and service-local Python tooling for actual backend runtime behavior

### Event Strategy

- keep event payloads minimal
- include `event_id`, `occurred_at`, and entity identifiers
- design consumers to be idempotent

### UI Scope

- do not build every possible CRM screen
- implement only the screens needed to demonstrate the core flows cleanly

## 9. Risks and Mitigations

### Risk: Federation complexity slows delivery

Mitigation:

- start with a minimal gateway and one simple federated query
- add schema breadth only after basic composition works

### Risk: Kafka integration consumes too much time

Mitigation:

- keep one workflow only
- avoid multiple topics and complex branching
- implement one consumer with one clear task-creation rule first

### Risk: Authorization becomes inconsistent across services

Mitigation:

- centralize identity at the gateway and Identity service
- still enforce authorization in each backend service
- add explicit permission tests for boundary cases

### Risk: UI grows too large

Mitigation:

- follow the limited screen set in [`frontend.md`](frontend.md)
- treat activity/task forms as modal or inline flows instead of building many separate pages

## 10. Recommended Testing Strategy

### Unit Tests

- deal status transition rules
- permission checks
- validation rules for parent-child company relationships
- task creation logic derived from events

### Integration Tests

- gateway to service query composition
- login and identity propagation
- GraphQL mutations for company, contact, and deal flows

### Event-Flow Tests

- `updateDealStatus` publishes expected event
- consumer creates expected task
- duplicate event delivery does not duplicate tasks

### Manual Verification

- create company as admin
- create contact
- create deal
- update deal status
- observe async task creation in UI
- verify access restrictions with a non-admin user

## 11. Suggested Milestone Breakdown

### Milestone 1

- workspace setup
- gateway skeleton
- identity service basic auth

### Milestone 2

- company/contact backend
- company/contact frontend

### Milestone 3

- deals backend
- deal frontend

### Milestone 4

- Kafka async workflow
- task backend and task UI visibility

### Milestone 5

- activity support
- authorization hardening
- tests and README

## 12. Definition of Done

The project is ready for submission when:

- all planned services run in Docker Compose
- frontend talks only to the GraphQL gateway
- company, contact, deal, task, and activity data are implemented in their owning services
- at least one Kafka-driven asynchronous workflow works end-to-end
- authorization is enforced server-side
- core tests exist for business logic and async flow
- README explains setup, architecture, and tradeoffs

## 13. Future Hardening Path

If this were extended further, the next improvements would be:

- stronger authentication and token lifecycle management
- outbox pattern for event publication
- dead-letter topic handling
- richer audit trails
- better task rule configuration
- full observability stack
- more granular role and membership model
