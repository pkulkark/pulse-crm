# Phase 8: Authorization Hardening

## Objective

Make access boundaries explicit, consistent, and enforced in every backend service.

## Scope

- admin-only mutations for company and contact management
- role-based access for deal, task, and activity operations
- service-level authorization checks

## Authorization Matrix

Use the phase-specific matrix in [phase-8-authorization-matrix.md](../api-contracts/phase-8-authorization-matrix.md).

The implementation should follow that matrix unless a clear technical reason requires a small adjustment. If the rules change, update the matrix doc in the same phase.

## Engineering Standards

- code quality must be industry-standard and production-level
- keep authorization rules explicit and testable
- do not overengineer a policy engine unless the simple role model becomes insufficient
- avoid overly defensive authorization code that repeats the same rule in every resolver body; centralize where practical and keep enforcement visible
- prefer denial by default for ambiguous access cases

## Work Breakdown

1. Confirm and implement the authorization matrix for `admin`, `manager`, and `sales_rep`.
2. Implement service-level authorization helpers or middleware where appropriate.
3. Enforce admin-only company/contact mutations.
4. Enforce authenticated reads across services.
5. Align allow/deny behavior across list and detail operations.
6. Add tests for allowed and forbidden access paths.

## Deliverables

- consistent server-side authorization behavior
- permission tests for critical data boundaries
- phase-specific authorization matrix documented and implemented

## Acceptance Criteria

- non-admin users cannot create or edit companies or contacts
- authenticated users can read CRM records regardless of company hierarchy position
- managers and `sales_rep` users can create and update deals
- managers can create and assign tasks
- `sales_rep` users can update only the status of tasks assigned to them
- managers can update only the status of tasks assigned to them, unless a broader admin privilege applies
- managers and `sales_rep` users can create activities
- authorization failures are clear and auditable
- implemented authorization behavior matches the documented Phase 8 matrix, or any deviation is documented

## Out of Scope

- fine-grained field masking per role
- cross-tenant sharing exceptions

## Recommended Verification

- test as admin, manager, and `sales_rep` users
- verify both allowed and denied queries/mutations
- inspect logs for authorization failure visibility
