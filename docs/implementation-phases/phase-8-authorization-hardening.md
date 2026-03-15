# Phase 8: Authorization Hardening

## Objective

Make access boundaries explicit, consistent, and enforced in every backend service.

## Scope

- admin-only mutations for company and contact management
- company-scoped read filtering
- parent-company visibility rules
- service-level authorization checks

## Engineering Standards

- code quality must be industry-standard and production-level
- keep authorization rules explicit and testable
- do not overengineer a policy engine unless the simple role/scope model becomes insufficient
- avoid overly defensive authorization code that repeats the same rule in every resolver body; centralize where practical and keep enforcement visible
- prefer denial by default for ambiguous access cases

## Work Breakdown

1. Define the final rule set for admin, manager, and `sales_rep` scopes.
2. Implement service-level authorization helpers or middleware where appropriate.
3. Enforce admin-only company/contact mutations.
4. Enforce company-scoped reads across services.
5. Implement parent-company visibility across child-company data.
6. Add tests for allowed and forbidden access paths.

## Deliverables

- consistent server-side authorization behavior
- explicit parent-child visibility rules
- permission tests for critical data boundaries

## Acceptance Criteria

- non-admin users cannot create or edit companies or contacts
- child-company users cannot access sibling-company data
- parent-company users can access allowed child-company data
- authorization failures are clear and auditable

## Out of Scope

- fine-grained field masking per role
- cross-tenant sharing exceptions

## Recommended Verification

- test as admin, manager, and `sales_rep` users
- verify both allowed and denied queries/mutations
- inspect logs for authorization failure visibility
