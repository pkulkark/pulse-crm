# Phase 1: GraphQL Gateway Skeleton

## Objective

Prove that the frontend and external clients communicate only with a single GraphQL gateway and that the gateway can compose responses from downstream services.

## Scope

- GraphQL gateway service bootstrap
- federation wiring
- request context propagation
- one minimal health-style federated query path
- public gateway GraphQL endpoint at `/`
- gateway health endpoint at `/health`

## Engineering Standards

- code quality must be industry-standard and production-level
- keep gateway behavior easy to trace and debug
- do not overengineer schema composition or add advanced gateway plugins prematurely
- avoid overly defensive branching around request handling; validate required context once and keep the flow simple
- prefer explicit request context objects over hidden global state

## Work Breakdown

1. Bootstrap the gateway service and expose a GraphQL endpoint.
2. Configure the gateway so the public GraphQL endpoint is `/` and the health endpoint is `/health`.
3. Define the initial federation configuration for downstream services.
4. Add a minimal health-style query path that proves composition works.
5. Prefer a simple field such as `serviceHealth` or `gatewayHealth` that resolves through at least one downstream service rather than designing a real business API this early.
6. Define the request context shape for user identity, role, and correlation IDs.
7. Add basic request logging and health endpoints.

## Deliverables

- running GraphQL gateway
- one working health-style query through the gateway to at least one downstream service
- request context shape defined for later phases
- gateway endpoint convention documented and implemented

## Acceptance Criteria

- a GraphQL client can query the gateway successfully
- the gateway reaches at least one downstream service
- the initial proof query is a health-style field, not a real business API contract
- request context is available to downstream resolvers in a consistent format
- the public GraphQL endpoint is `/` and the health endpoint is `/health`

## Out of Scope

- full schema
- full auth enforcement
- advanced caching or query cost controls

## Recommended Verification

- query the gateway directly using the health-style field
- verify downstream calls are visible in logs
- verify a broken downstream service produces a clear gateway error
