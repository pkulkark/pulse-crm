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

## Engineering Standards

- code quality must be industry-standard and production-level
- keep the UI intentionally small and task-oriented
- do not overengineer component systems, design tokens, or client-side state abstractions beyond what the chosen screens need
- avoid overly defensive client logic that duplicates backend authorization or validation rules
- prefer straightforward data-fetching patterns and explicit loading/error states

## Work Breakdown

1. Set up Apollo Client and gateway connectivity.
2. Implement login and authenticated app shell behavior.
3. Implement company list and company detail screens.
4. Implement create/edit company and create/edit contact flows for admin users.
5. Implement deal list and deal detail screens.
6. Implement task list and task update interactions.
7. Implement activity and task create/edit forms as modals or inline flows.
8. Add empty, loading, and error states.
9. Add polling or refetch behavior to surface async task creation after deal status changes.

## Deliverables

- working frontend connected only to the GraphQL gateway
- visible role-based actions in the UI
- main CRM workflows available to internal users

## Acceptance Criteria

- admin can create a company and contact from the UI
- a user can create a deal and update its status from the UI
- task list reflects async-created follow-up tasks after status updates
- unauthorized actions are hidden or disabled in the UI, but still enforced server-side

## Out of Scope

- polished design system work
- advanced offline/client cache strategies
- analytics instrumentation beyond basic logging hooks

## Recommended Verification

- execute the documented frontend flows in [`frontend.md`](/Users/poojakulkarni/SampleCRM/docs/frontend.md)
- verify loading and error states manually
- verify the UI recovers cleanly from backend errors

