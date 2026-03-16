# Phase 6 API Contract: CRM Relationships Service, Part 2

## Purpose

This document defines the minimum GraphQL contract for Phase 6.

The goal is to support:

- task reads and updates
- task filtering
- activity creation and activity history reads
- access to Kafka-generated tasks through the normal task API

This contract is intentionally limited to `Task` and `Activity`. It assumes `Company` and `Contact` already exist in this service and that `Deal` may be referenced by ID and resolved through federation.

## Contract Principles

- keep the distinction clear between work items (`Task`) and historical records (`Activity`)
- use enums for constrained values
- use input types for mutations
- expose nested object fields where they help the frontend
- keep filtering simple and aligned with the documented UI

## Ownership

This service owns:

- `Task`
- `Activity`

This service does not own:

- `User`
- `Deal`

It also continues to own:

- `Company`
- `Contact`

## Schema Contract

```graphql
enum TaskStatus {
  OPEN
  COMPLETED
}

enum TaskPriority {
  LOW
  MEDIUM
  HIGH
}

enum ActivityType {
  CALL
  EMAIL
  MEETING
  NOTE
}

type Task {
  id: ID!
  title: String!
  companyId: ID!
  contactId: ID
  dealId: ID
  userId: ID!
  status: TaskStatus!
  dueDate: String
  priority: TaskPriority!
  company: Company!
  contact: Contact
  deal: Deal
}

type Activity {
  id: ID!
  companyId: ID!
  contactId: ID
  dealId: ID
  userId: ID!
  type: ActivityType!
  details: String!
  occurredAt: String!
  company: Company!
  contact: Contact
  deal: Deal
}

input TaskFiltersInput {
  status: TaskStatus
  userId: ID
  dueBefore: String
}

input CreateTaskInput {
  title: String!
  companyId: ID!
  contactId: ID
  dealId: ID
  userId: ID!
  dueDate: String
  priority: TaskPriority!
}

input UpdateTaskInput {
  taskId: ID!
  title: String
  status: TaskStatus
  dueDate: String
  priority: TaskPriority
}

input CreateActivityInput {
  companyId: ID!
  contactId: ID
  dealId: ID
  userId: ID!
  type: ActivityType!
  details: String!
  occurredAt: String!
}

type Query {
  tasks(filters: TaskFiltersInput): [Task!]!
  activities(companyId: ID, dealId: ID, contactId: ID): [Activity!]!
}

type Mutation {
  createTask(input: CreateTaskInput!): Task!
  updateTask(input: UpdateTaskInput!): Task!
  createActivity(input: CreateActivityInput!): Activity!
}
```

## Operation Notes

### `tasks`

Purpose:

- return tasks visible to the current user

Behavior:

- supports simple filtering by status, assignee, and due date
- includes both manually created tasks and Kafka-generated tasks

### `activities`

Purpose:

- return activity history for a company, contact, or deal context

Behavior:

- at least one filter should usually be provided by the caller
- returns activities for the requested company, contact, or deal filters

### `createTask`

Purpose:

- create a follow-up work item

Behavior:

- requires a valid owning company
- contact and deal are optional
- if contact or deal are present, they must belong to the same company

### `updateTask`

Purpose:

- update task fields, especially status

Behavior:

- supports changing task status from `OPEN` to `COMPLETED`
- may support partial updates for title, due date, or priority

### `createActivity`

Purpose:

- log a completed interaction

Behavior:

- requires a valid owning company
- contact and deal are optional
- if provided, they must belong to the same company

## Example Operations

### Query Example: Task List

```graphql
query {
  tasks(filters: { status: OPEN }) {
    id
    title
    status
    priority
    dueDate
    company {
      id
      name
    }
    deal {
      id
      status
    }
  }
}
```

### Mutation Example: Create Task

```graphql
mutation {
  createTask(
    input: {
      title: "Schedule follow-up"
      companyId: "company_1"
      dealId: "deal_1"
      userId: "user_1"
      priority: HIGH
    }
  ) {
    id
    title
    status
  }
}
```

### Mutation Example: Update Task

```graphql
mutation {
  updateTask(input: { taskId: "task_1", status: COMPLETED }) {
    id
    status
  }
}
```

### Mutation Example: Create Activity

```graphql
mutation {
  createActivity(
    input: {
      companyId: "company_1"
      dealId: "deal_1"
      userId: "user_1"
      type: CALL
      details: "Discussed follow-up timeline"
      occurredAt: "2026-03-15T16:00:00Z"
    }
  ) {
    id
    type
    details
  }
}
```

## Federation Notes

- `companyId` and `contactId` are resolved within this service because `Company` and `Contact` are owned here
- `dealId` may be exposed as a nested `deal` field through federation
- `userId` may remain an ID-only field for now unless there is a clear frontend need for a nested `user`

## Validation Rules

- `companyId` is required for both tasks and activities
- if `contactId` is present, it must reference a contact for the same company
- if `dealId` is present, it must reference a deal for the same company
- `priority`, `status`, and `type` must be valid enum values
- `occurredAt` is required for activity creation

## Authorization Rules

- all task and activity operations require an authenticated user
- authenticated users can read tasks and activities across CRM data
- `admin` and `manager` can create tasks
- `admin` can update task fields broadly
- `manager` and `sales_rep` can update only the status of tasks assigned to them
- authenticated users in supported business roles can create activities

## Error Handling Expectations

- invalid company/contact/deal relationships should produce clear validation errors
- inaccessible records should be filtered out or return a consistent authorization/not-found response based on the chosen GraphQL error approach
- invalid task updates should produce clear validation errors rather than silent no-ops

## Implementation Notes

- if the implementation prefers `task(id: ID!)` later, it can be added without breaking this minimum contract
- if `dueDate` and `occurredAt` are represented as proper GraphQL scalar types later, this contract can evolve from `String` to a dedicated datetime scalar without changing the service boundary
