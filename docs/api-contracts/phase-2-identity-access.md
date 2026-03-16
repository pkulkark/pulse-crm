# Phase 2 API Contract: Identity and Access Service

## Purpose

This document defines the minimum GraphQL contract for Phase 2.

The goal is to support:

- user authentication for internal CRM users
- retrieval of the current authenticated user
- propagation of trusted identity and role context to downstream services

This contract is intentionally small. It should be implemented cleanly and kept stable for the remainder of the system unless a strong reason emerges to change it.

## Contract Principles

- keep the API minimal
- use explicit GraphQL types and inputs
- use enums for constrained values such as roles
- prefer non-null fields where the backend can guarantee them
- avoid exposing authentication internals beyond what the frontend and gateway actually need

## Ownership

This service owns:

- `User`
- authentication result data needed by the frontend and gateway

This service does not own:

- company hierarchy records
- CRM entities such as deals, contacts, tasks, or activities

## Schema Contract

```graphql
enum UserRole {
  ADMIN
  MANAGER
  SALES_REP
}

type User {
  id: ID!
  companyId: ID
  name: String!
  email: String!
  role: UserRole!
}

type AuthPayload {
  token: String!
  user: User!
}

input LoginInput {
  email: String!
  password: String!
}

type Query {
  me: User
}

type Mutation {
  login(input: LoginInput!): AuthPayload!
}
```

## Operation Notes

### `me`

Purpose:

- return the currently authenticated user

Behavior:

- returns the authenticated `User`
- returns `null` if the request is unauthenticated

Auth rule:

- requires a valid authenticated context to return a user

### `login`

Purpose:

- authenticate a user and return the minimal payload needed by the frontend

Behavior:

- validates credentials
- returns a token and the authenticated user
- returns an authorization error for invalid credentials

Auth rule:

- public operation

## Example Operations

### Query Example

```graphql
query {
  me {
    id
    companyId
    name
    email
    role
  }
}
```

### Mutation Example

```graphql
mutation {
  login(input: { email: "admin@example.com", password: "secret" }) {
    token
    user {
      id
      name
      role
      companyId
    }
  }
}
```

## Gateway and Federation Notes

- the gateway should call `login` and `me` through this service
- the gateway should validate or trust the token according to the chosen auth approach and pass trusted user context downstream
- downstream services should rely on trusted context from the gateway rather than frontend-provided role claims
- `companyId`, when present, represents internal organizational context supplied by identity and is not a customer-data authorization boundary in this phase

## Validation Rules

- `email` must be a valid email format
- `password` is required for `login`
- `companyId` on `User` is optional and may be omitted when the identity system does not use it
- `role` must be one of the supported `UserRole` enum values

## Error Handling Expectations

- invalid credentials should produce a clear authentication error
- unauthenticated access to `me` should return `null` or a consistent unauthenticated error based on the chosen GraphQL error approach
- internal failures should not leak sensitive auth details

## Implementation Notes

- if the implementation chooses a session-based mechanism rather than a token returned from GraphQL, `me` remains mandatory and `login` may be adapted accordingly
- if `login` is adapted, the phase implementation must document the final chosen shape and keep the frontend contract explicit
