# Phase 3 API Contract: CRM Relationships Service, Part 1

## Purpose

This document defines the minimum GraphQL contract for Phase 3.

The goal is to support:

- company creation and editing
- contact creation and editing
- company list and company detail reads
- contact reads needed by the frontend and later service composition
- parent-child company hierarchy

This contract is intentionally limited to `Company` and `Contact`. It does not include `Task` or `Activity`, which belong to a later phase.

## Contract Principles

- keep the schema small and directly aligned with the current frontend and service needs
- expose useful nested object shapes instead of only raw foreign-key IDs
- use input types for mutations
- keep nullability explicit
- restrict write operations through server-side authorization, not schema shape alone

## Ownership

This service owns:

- `Company`
- `Contact`

This service does not own:

- `User`
- `Deal`
- `Task`
- `Activity`

## Schema Contract

```graphql
type Company {
  id: ID!
  name: String!
  parentCompanyId: ID
  parentCompany: Company
  childCompanies: [Company!]!
  contacts: [Contact!]!
}

type Contact {
  id: ID!
  companyId: ID!
  company: Company!
  name: String!
  email: String!
  jobTitle: String
}

input CreateCompanyInput {
  name: String!
  parentCompanyId: ID
}

input UpdateCompanyInput {
  companyId: ID!
  name: String!
  parentCompanyId: ID
}

input CreateContactInput {
  companyId: ID!
  name: String!
  email: String!
  jobTitle: String
}

input UpdateContactInput {
  contactId: ID!
  name: String!
  email: String!
  jobTitle: String
}

type Query {
  companies: [Company!]!
  company(id: ID!): Company
  contact(id: ID!): Contact
}

type Mutation {
  createCompany(input: CreateCompanyInput!): Company!
  updateCompany(input: UpdateCompanyInput!): Company!
  createContact(input: CreateContactInput!): Contact!
  updateContact(input: UpdateContactInput!): Contact!
}
```

## Operation Notes

### `companies`

Purpose:

- return the set of companies visible to the current user

Behavior:

- returns only companies within the current user’s authorized scope

### `company`

Purpose:

- return one company by ID

Behavior:

- includes parent company, child companies, and contacts when requested
- returns `null` if not found or not visible to the current user

### `contact`

Purpose:

- return one contact by ID

Behavior:

- returns `null` if not found or not visible to the current user

### `createCompany` and `updateCompany`

Purpose:

- create or update company records

Behavior:

- admin-only
- parent company is optional
- hierarchy rules must be validated

### `createContact` and `updateContact`

Purpose:

- create or update contacts under a company

Behavior:

- admin-only
- contact must belong to exactly one company
- contact email should be unique within a company

## Example Operations

### Query Example: Company Detail

```graphql
query {
  company(id: "company_1") {
    id
    name
    parentCompany {
      id
      name
    }
    childCompanies {
      id
      name
    }
    contacts {
      id
      name
      email
    }
  }
}
```

### Mutation Example: Create Company

```graphql
mutation {
  createCompany(input: { name: "BrightCo", parentCompanyId: "parent_1" }) {
    id
    name
    parentCompanyId
  }
}
```

### Mutation Example: Create Contact

```graphql
mutation {
  createContact(
    input: {
      companyId: "company_1"
      name: "Alice Johnson"
      email: "alice@brightco.com"
      jobTitle: "CEO"
    }
  ) {
    id
    name
    email
    company {
      id
      name
    }
  }
}
```

## Federation Notes

- `Company` and `Contact` are the source-of-truth records for these entities
- later services may reference `companyId` and `contactId`, but should not own company/contact data
- nested fields such as `company` on `Contact` are resolved within this service

## Validation Rules

- company name is required
- a company cannot be its own parent
- company hierarchy must not create cycles
- contact must reference an existing company
- contact email must be valid
- contact email must be unique within the same company

## Authorization Rules

- `companies`, `company`, and `contact` require an authenticated user
- visible records are filtered by the current user’s company scope
- `createCompany`, `updateCompany`, `createContact`, and `updateContact` are admin-only

## Error Handling Expectations

- invalid hierarchy changes should produce a clear validation error
- admin-only mutation violations should produce an authorization error
- record lookups outside the user’s scope should return `null` or a consistent authorization/not-found response based on the chosen GraphQL error approach

## Implementation Notes

- if `company(id)` and `contact(id)` are implemented as nullable fields, callers must handle missing values cleanly
- if later phases require company search or pagination, those can be added without breaking this minimum contract

