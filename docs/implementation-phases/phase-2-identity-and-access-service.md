# Phase 2: Identity and Access Service

## Objective

Implement internal user identity and role awareness so later services can authorize requests correctly.

## Scope

- `User` model
- authentication flow suitable for the initial implementation
- role-aware request context
- GraphQL operations such as `me`

## API Contract

Use the phase-specific contract in [phase-2-identity-access.md](../api-contracts/phase-2-identity-access.md).

The implementation should follow that contract unless a clear technical reason requires a small adjustment. If the contract changes, update the contract doc in the same phase.

## Engineering Standards

- code quality must be industry-standard and production-level
- keep authentication simple, explicit, and explainable
- do not overengineer identity with unnecessary providers or permission matrices at this stage
- avoid overly defensive auth code that duplicates checks in multiple layers without clear ownership
- validate credentials and tokens at the boundary, then pass trusted context downstream

## Work Breakdown

1. Implement the `User` model and migrations.
2. Seed at least one admin user and one non-admin user.
3. Confirm and implement the API contract for `login` and `me`.
4. Implement the chosen login/authentication mechanism.
5. Expose `me` and any minimal user lookup needed by the system.
6. Add user identity and role fields to gateway-to-service context propagation.
7. Add tests for login success, login failure, and role propagation.

## Deliverables

- working user authentication
- trusted user context available downstream
- role information exposed to later services
- phase-specific API contract documented and implemented

## Acceptance Criteria

- login works end-to-end
- `me` returns the authenticated user and role
- requests without valid identity are rejected
- downstream services can consume trusted user context
- implemented schema matches the documented Phase 2 contract, or any deviation is documented

## Out of Scope

- SSO
- refresh-token lifecycle management
- multi-company membership

## Recommended Verification

- authenticate as admin and non-admin users
- verify user context is visible in gateway and downstream logs
- verify unauthenticated requests fail predictably
