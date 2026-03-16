# Phase 8 Authorization Matrix

## Purpose

This document defines the authorization matrix for Phase 8.

It is the source of truth for:

- role-based access rules
- authenticated read behavior
- expected allow/deny outcomes for key operations

This is not a GraphQL API contract. It is an authorization contract for backend enforcement and verification.

## User Model

- all `User` records represent internal host-company users of the CRM
- customer companies are CRM data records, not application users
- company hierarchy organizes CRM data but is not used as a per-user access boundary
- access control is determined by authenticated role checks

## Roles

- `admin`
- `manager`
- `sales_rep`

## Core Rules

### Global Principles

- all business operations require an authenticated user unless explicitly documented otherwise
- authorization is enforced server-side
- UI visibility is a convenience only and is not sufficient as enforcement
- deny by default for missing authentication or disallowed role actions

### Role Summary

#### `admin`

- global internal operator
- can create and edit companies across all customer-company records
- can create and edit contacts across all customer-company records
- can read and mutate deals, tasks, and activities across all customer-company records

#### `manager`

- can read company, contact, deal, task, and activity data across all customer-company records
- can create and update deals across all customer-company records
- can create tasks and assign them by `userId`
- can update the status of tasks assigned to them
- can create activities across all customer-company records
- cannot create or edit companies or contacts

#### `sales_rep`

- can read company, contact, deal, task, and activity data across all customer-company records
- can create and update deals across all customer-company records
- can update the status of tasks assigned to them
- can create activities across all customer-company records
- cannot create tasks
- cannot create or edit companies or contacts

## Operation Matrix

### Company and Contact Operations

| Operation | Admin | Manager | Sales Rep | Unauthenticated |
|---|---|---|---|---|
| `companies` | Allow | Allow | Allow | Deny |
| `company(id)` | Allow | Allow | Allow | Deny |
| `contact(id)` | Allow | Allow | Allow | Deny |
| `createCompany` | Allow | Deny | Deny | Deny |
| `updateCompany` | Allow | Deny | Deny | Deny |
| `createContact` | Allow | Deny | Deny | Deny |
| `updateContact` | Allow | Deny | Deny | Deny |

### Deal Operations

| Operation | Admin | Manager | Sales Rep | Unauthenticated |
|---|---|---|---|---|
| `deals` | Allow | Allow | Allow | Deny |
| `deal(id)` | Allow | Allow | Allow | Deny |
| `createDeal` | Allow | Allow | Allow | Deny |
| `updateDealStatus` | Allow | Allow | Allow | Deny |

### Task and Activity Operations

| Operation | Admin | Manager | Sales Rep | Unauthenticated |
|---|---|---|---|---|
| `tasks` | Allow | Allow | Allow | Deny |
| `createTask` | Allow | Allow | Deny | Deny |
| `updateTask` | Allow | Allow, assigned-task status only | Allow, assigned-task status only | Deny |
| `activities` | Allow | Allow | Allow | Deny |
| `createActivity` | Allow | Allow | Allow | Deny |

## Read Filtering Rules

- authenticated list queries may return records across all customer companies
- detail queries return the record when it exists and the request is authenticated
- unauthenticated reads should return an authentication error or `null`, consistent with the service contract

## Cross-Service Enforcement Notes

- the gateway should propagate trusted user identity context used by the services
- each service must still enforce authorization for the records it owns
- `Deals` must enforce deal authorization based on authentication and role rules
- `CRM Relationships` must enforce company, contact, task, and activity authorization based on authentication and role rules

## Error Handling Expectations

- admin-only violations should return a clear authorization error
- task assignment and task-field restrictions should return a clear authorization error
- unauthenticated reads should fail clearly
- authorization failures should be logged with enough context for debugging and auditing

## Minimum Test Matrix

At minimum, test these cases:

- admin can create and update company/contact globally
- manager cannot create or update company/contact
- sales_rep cannot create or update company/contact
- manager and sales_rep can read company/contact/deal/task/activity records across companies
- manager and sales_rep can create and update deals across companies
- manager can create tasks and assign them
- sales_rep cannot create tasks
- manager and sales_rep can update the status of tasks assigned to them
- non-admin users cannot edit task fields other than status
- manager and sales_rep can create activities across companies
- unauthenticated reads are denied consistently

## Implementation Notes

- if the codebase already uses a consistent `null for inaccessible detail` pattern, preserve it across services
- if a small adjustment to this matrix is required by an already-implemented phase, update this document in the same change and document why
