# Phase 7 Frontend-to-API Mapping

## Purpose

This document maps the frontend screens in Phase 7 to the GraphQL operations and event-driven behaviors already defined in earlier phases.

This is not a new API contract. It is a consumption map for the frontend.

## Why This Exists

By Phase 7, the frontend depends on:

- the Identity and Access contract from Phase 2
- the Company and Contact contract from Phase 3
- the Deals contract from Phase 4
- the Task and Activity contract from Phase 6
- the asynchronous workflow behavior from Phase 5

Those contracts are already defined, but they are spread across multiple files. This mapping keeps the frontend implementation focused and prevents the UI phase from inventing new API requirements unnecessarily.

## Screen-to-API Mapping

### Login Screen

Primary operations:

- `login`
- `me`

Source contract:

- [phase-2-identity-access.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-2-identity-access.md)

Notes:

- use `login` to authenticate
- use `me` to restore authenticated app state and role-aware UI behavior

### Company List Screen

Primary operations:

- `companies`

Source contract:

- [phase-3-crm-relationships-part-1.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-3-crm-relationships-part-1.md)

Notes:

- list should show only companies visible to the current user
- UI may optionally render parent/child indicators from the returned company shape

### Company Detail Screen

Primary operations:

- `company(id)`
- optionally `tasks(filters)`
- optionally `activities(companyId: ...)`

Source contracts:

- [phase-3-crm-relationships-part-1.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-3-crm-relationships-part-1.md)
- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

Notes:

- use `company(id)` for core company, child-company, and contact data
- use `tasks` and `activities` to populate the company context sections if implemented in this phase

### Create/Edit Company

Primary operations:

- `createCompany`
- `updateCompany`

Source contract:

- [phase-3-crm-relationships-part-1.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-3-crm-relationships-part-1.md)

Notes:

- admin-only in the UI
- backend remains the source of truth for authorization

### Create/Edit Contact

Primary operations:

- `createContact`
- `updateContact`

Source contract:

- [phase-3-crm-relationships-part-1.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-3-crm-relationships-part-1.md)

Notes:

- admin-only in the UI
- contact create/edit flows should remain company-scoped

### Deal List Screen

Primary operations:

- `deals`

Source contract:

- [phase-4-deals-service.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-4-deals-service.md)

Notes:

- list can render nested company and primary contact data via federation

### Deal Detail Screen

Primary operations:

- `deal(id)`
- `updateDealStatus`
- optionally `activities(dealId: ...)`
- optionally `tasks(filters)` scoped in the UI to the current deal

Source contracts:

- [phase-4-deals-service.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-4-deals-service.md)
- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

Notes:

- after `updateDealStatus`, refetch or poll task data to surface asynchronous follow-up tasks

### Create Deal

Primary operations:

- `createDeal`

Source contract:

- [phase-4-deals-service.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-4-deals-service.md)

Notes:

- use the company and contact data already loaded in the UI to drive the form choices where possible

### Task List Screen

Primary operations:

- `tasks(filters)`
- `updateTask`

Source contract:

- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

Notes:

- task list should show both manually created and Kafka-generated tasks
- use contract-supported filters only

### Create/Edit Task

Primary operations:

- `createTask`
- `updateTask`

Source contract:

- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

### Activity Create Form

Primary operations:

- `createActivity`

Source contract:

- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

### Activity History Views

Primary operations:

- `activities(companyId: ...)`
- `activities(dealId: ...)`
- `activities(contactId: ...)`

Source contract:

- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

## Async UX Mapping

### Deal status update to follow-up task creation

User action:

- `updateDealStatus`

Backend behavior:

- publishes `deal.status_changed`
- CRM Relationships consumer creates follow-up tasks

Frontend expectation:

- update the deal detail view immediately after the mutation
- refetch or poll task data shortly after
- show a non-blocking message indicating follow-up tasks may appear shortly

Source references:

- [phase-4-deals-service.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-4-deals-service.md)
- [phase-5-deal-status-changed-event.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-5-deal-status-changed-event.md)
- [phase-6-crm-relationships-part-2.md](/Users/poojakulkarni/SampleCRM/docs/api-contracts/phase-6-crm-relationships-part-2.md)

## Implementation Notes

- Phase 7 should consume existing API and event behavior rather than redefine it
- if the frontend exposes a contract gap, update the relevant earlier contract doc rather than creating an unrelated new frontend-only API shape
- frontend data requirements should stay aligned with the documented contracts

