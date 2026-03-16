# Phase 7: Frontend Screens

## Objective

Deliver the smallest complete frontend surface that proves the CRM workflows end-to-end.

## Scope

- React frontend
- Apollo Client integration
- login
- company/contact flows
- deal flows
- task list
- activity and task forms

## Frontend-to-API Mapping

Use the consumption map in [phase-7-frontend-api-mapping.md](../api-contracts/phase-7-frontend-api-mapping.md).

This phase should consume the existing contracts from earlier phases rather than define a new API contract unless a real contract gap is discovered.

## Engineering Standards

- code quality must be industry-standard and production-level
- keep the UI intentionally small and task-oriented
- do not overengineer component systems, design tokens, or client-side state abstractions beyond what the chosen screens need
- avoid overly defensive client logic that duplicates backend authorization or validation rules
- prefer straightforward data-fetching patterns and explicit loading/error states

## Work Breakdown

1. Set up Apollo Client and gateway connectivity.
2. Implement login and authenticated app shell behavior.
3. Confirm the frontend-to-API mapping against the existing contracts before building screens.
4. Implement company list and company detail screens.
5. Implement create/edit company and create/edit contact flows for admin users.
6. Implement deal list and deal detail screens.
7. Implement task list and task update interactions.
8. Implement activity and task create/edit forms as modals or inline flows.
9. Add empty, loading, and error states.
10. Add polling or refetch behavior to surface async task creation after deal status changes.

## Deliverables

- working frontend connected only to the GraphQL gateway
- visible role-based actions in the UI
- main CRM workflows available to internal users
- frontend-to-API mapping documented and followed

## Acceptance Criteria

- admin can create a company and contact from the UI
- a user can create a deal and update its status from the UI
- task list reflects async-created follow-up tasks after status updates
- unauthorized actions are hidden or disabled in the UI, but still enforced server-side
- frontend behavior matches the existing contracts, or any contract gap is documented and pushed back into the relevant earlier contract doc

## Out of Scope

- polished design system work
- advanced offline/client cache strategies
- analytics instrumentation beyond basic logging hooks

## Recommended Verification

- execute the documented frontend flows in [`frontend.md`](../frontend.md)
- verify loading and error states manually
- verify the UI recovers cleanly from backend errors
