# Phase 4 API Contract: Deals Service

## Purpose

This document defines the minimum GraphQL contract for Phase 4.

The goal is to support:

- deal creation
- deal list and detail reads
- deal status updates
- nested GraphQL access to related company and primary contact fields through federation

This contract is intentionally limited to `Deal` and its immediate workflow behavior. It does not include asynchronous Kafka event behavior, which is covered in the next phase.

## Contract Principles

- keep the schema small and aligned with the current CRM flows
- use enums for lifecycle states
- use input types for mutations
- expose nested fields needed by the frontend, even when the service owns only the reference IDs
- keep status transition behavior explicit and easy to reason about

## Ownership

This service owns:

- `Deal`
- deal status lifecycle rules

This service does not own:

- `Company`
- `Contact`
- `Task`
- `Activity`
- `User`

## Schema Contract

```graphql
enum DealStatus {
  NEW
  QUALIFIED
  WON
  LOST
}

type Deal {
  id: ID!
  companyId: ID!
  primaryContactId: ID
  status: DealStatus!
  company: Company!
  primaryContact: Contact
}

input CreateDealInput {
  companyId: ID!
  primaryContactId: ID
  status: DealStatus!
}

input UpdateDealStatusInput {
  dealId: ID!
  status: DealStatus!
}

type Query {
  deals: [Deal!]!
  deal(id: ID!): Deal
}

type Mutation {
  createDeal(input: CreateDealInput!): Deal!
  updateDealStatus(input: UpdateDealStatusInput!): Deal!
}
```

## Operation Notes

### `deals`

Purpose:

- return the set of deals visible to the current user

Behavior:

- returns only deals within the current user’s authorized company scope

### `deal`

Purpose:

- return one deal by ID

Behavior:

- returns `null` if not found or not visible to the current user

### `createDeal`

Purpose:

- create a new deal for a company

Behavior:

- requires a valid `companyId`
- `primaryContactId` is optional
- if `primaryContactId` is present, it must belong to the same company

### `updateDealStatus`

Purpose:

- update the current status of a deal

Behavior:

- applies explicit status validation rules
- returns the updated deal
- later phases may publish an event after a successful status update

## Example Operations

### Query Example: Deal Detail

```graphql
query {
  deal(id: "deal_1") {
    id
    status
    company {
      id
      name
    }
    primaryContact {
      id
      name
      email
    }
  }
}
```

### Mutation Example: Create Deal

```graphql
mutation {
  createDeal(
    input: {
      companyId: "company_1"
      primaryContactId: "contact_1"
      status: NEW
    }
  ) {
    id
    status
    companyId
    primaryContactId
  }
}
```

### Mutation Example: Update Deal Status

```graphql
mutation {
  updateDealStatus(input: { dealId: "deal_1", status: QUALIFIED }) {
    id
    status
  }
}
```

## Federation Notes

- `companyId` and `primaryContactId` are stored in this service
- `company` and `primaryContact` are exposed as nested GraphQL fields for frontend convenience
- those nested fields are resolved through federation and do not imply ownership of company/contact data in this service

## Validation Rules

- `companyId` must reference an existing company
- if `primaryContactId` is present, it must reference an existing contact for the same company
- `status` must be a valid `DealStatus` enum value
- status changes must follow the explicit transition rules chosen by the implementation

## Authorization Rules

- `deals` and `deal` require an authenticated user
- visible deals are filtered by the current user’s company scope
- `createDeal` and `updateDealStatus` require an authenticated user within the allowed company scope

## Error Handling Expectations

- invalid company/contact references should produce clear validation errors
- invalid status transitions should produce clear domain validation errors
- inaccessible deals should return `null` or a consistent authorization/not-found response based on the chosen GraphQL error approach

## Implementation Notes

- if later phases add pagination or deal filtering, they can extend `deals` without breaking this minimum contract
- if the implementation chooses to default newly created deals to `NEW`, the contract may be simplified by making `status` optional in `CreateDealInput`, but any such change should be documented here in the same phase

