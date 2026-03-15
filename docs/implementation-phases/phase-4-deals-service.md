# Phase 4: Deals Service

## Objective

Implement sales opportunities with clear lifecycle ownership in a dedicated service.

## Scope

- `Deal`
- deal creation
- deal detail and list reads
- deal status transitions
- federation references to company and contact

## Engineering Standards

- code quality must be industry-standard and production-level
- keep deal state transitions explicit and easy to test
- do not overengineer workflow engines or configuration-driven state machines unless they are truly needed
- avoid overly defensive status-transition code with excessive indirection; a small explicit transition policy is preferable
- keep reference validation clear when linking deals to companies and contacts

## Work Breakdown

1. Implement the `Deal` model and migrations.
2. Implement `createDeal`.
3. Implement `updateDealStatus`.
4. Validate `company_id` and `primary_contact_id` relationships.
5. Implement deal list and detail queries.
6. Add federation fields for company and primary contact references.
7. Add tests for valid and invalid status transitions.

## Deliverables

- working deal persistence
- deal list/detail queries
- status transition logic
- gateway access to deal data with federated company/contact views

## Acceptance Criteria

- a deal can be created for a company
- a deal status can be updated through the gateway
- invalid references or transitions are rejected clearly
- company and primary contact resolve through federation

## Out of Scope

- Kafka event publication reliability hardening beyond what is needed for the next phase
- advanced deal analytics

## Recommended Verification

- create a deal with and without a primary contact
- update status and verify the persisted change
- verify federated reads include company/contact data

