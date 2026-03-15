# CRM Frontend Screens and User Actions

## 1. Purpose

This document describes the frontend surface for the CRM system: the main screens, what data each screen shows, and what actions users can perform.

The frontend is used only by internal CRM users. External contacts and customers do not log in to this system.

The frontend communicates only with the GraphQL gateway.

## 2. Role Assumptions

The initial UI assumes three internal roles:

- `admin`
- `manager`
- `sales_rep`

High-level permission expectations:

- `admin` can create and edit companies and contacts
- `manager` can view company data across permitted company scope and manage deals, tasks, and activities
- `sales_rep` can work with deals, activities, and tasks in their allowed company scope

For the initial implementation, company and contact creation and editing are restricted to `admin`.

## 3. UX Principles

- keep the UI small and task-oriented
- show only actions the current user is authorized to perform
- make company context visible on deal, task, and activity screens
- handle loading, empty, and error states clearly
- reflect eventual consistency for Kafka-driven updates

## 4. Main Screens

### 4.1 Login Screen

Purpose:

- authenticate the internal user

Visible data:

- email/username field
- password field

Actions:

- sign in
- show authentication error if credentials are invalid

### 4.2 Company List Screen

Purpose:

- browse companies the current user is allowed to see
- create a new company if the user is an admin

Visible data:

- company name
- parent/child indicator
- parent company name if applicable
- basic counts, if desired, such as contacts or open deals

Actions:

- search companies
- filter by parent or child companies
- open a company detail page
- create company (`admin` only)

### 4.3 Create/Edit Company Screen

Purpose:

- create a new company record or edit an existing one

Visible fields:

- company name
- parent company selector (optional)

Actions:

- save company (`admin` only)
- update company (`admin` only)
- cancel

Validation examples:

- company name is required
- a company cannot be its own parent

### 4.4 Company Detail Screen

Purpose:

- act as the main CRM relationship page for a company

Visible data:

- company name
- parent company, if any
- child companies, if any
- contacts for the company
- recent activities
- open and upcoming tasks
- deals associated with the company

Actions:

- edit company (`admin` only)
- add contact (`admin` only)
- edit contact (`admin` only)
- create deal
- log activity
- create task
- open deal detail
- open task detail, if implemented

### 4.5 Create/Edit Contact Screen

Purpose:

- create or update a contact under a company

Visible fields:

- company
- contact name
- email
- job title

Actions:

- save contact (`admin` only)
- update contact (`admin` only)
- cancel

Validation examples:

- contact name is required
- email should be valid
- contact email should be unique within the company

### 4.6 Deal List Screen

Purpose:

- show deals the user is allowed to access

Visible data:

- deal identifier or title
- company
- primary contact, if set
- status
- last updated time

Actions:

- search deals
- filter by status
- open deal detail
- create deal

### 4.7 Create Deal Screen

Purpose:

- create a new deal attached to a company

Visible fields:

- company selector
- primary contact selector (optional, filtered by company)
- initial status

Actions:

- save deal
- cancel

Validation examples:

- company is required
- if a primary contact is selected, it must belong to the chosen company

### 4.8 Deal Detail Screen

Purpose:

- view and update one deal

Visible data:

- company
- primary contact
- status
- recent activity related to the deal
- open tasks related to the deal

Actions:

- update deal status
- log activity against the deal
- create task against the deal

Async behavior:

- after a deal status update, the deal should update immediately
- follow-up tasks created by Kafka may appear shortly after
- the UI should indicate that downstream updates may still be processing

### 4.9 Activity Create Form

Purpose:

- log a completed interaction

Visible fields:

- company
- contact (optional)
- deal (optional)
- activity type
- details
- occurred at

Actions:

- save activity
- cancel

Examples:

- call completed
- meeting held
- follow-up email sent

### 4.10 Task List Screen

Purpose:

- show follow-up work items for the current user or current company scope

Visible data:

- title
- company
- contact, if any
- deal, if any
- assignee
- due date
- priority
- status

Actions:

- filter by status
- filter by due date
- filter by assignee
- open a task
- create task
- update task status

### 4.11 Create/Edit Task Form

Purpose:

- create or update a follow-up work item

Visible fields:

- title
- company
- contact (optional)
- deal (optional)
- assignee
- due date
- priority
- status

Actions:

- save task
- update task
- mark task complete
- cancel

Validation examples:

- title is required
- company is required
- contact and deal, if provided, must belong to the selected company

## 5. Primary Frontend Flows

### Flow A: Create Company and Contact

1. Admin opens the company list.
2. Admin clicks `Create Company`.
3. Admin enters the company name and optional parent company.
4. Admin saves the company.
5. Admin opens the company detail page.
6. Admin creates one or more contacts for that company.

### Flow B: Create and Progress a Deal

1. User opens a company detail page.
2. User clicks `Create Deal`.
3. User selects the company and optional primary contact.
4. User saves the deal.
5. User later opens the deal detail screen.
6. User updates the deal status.

### Flow C: Kafka-Driven Follow-Up Creation

1. User updates a deal status, for example from `new` to `qualified`.
2. Frontend shows the updated deal status immediately.
3. Backend publishes `deal.status_changed`.
4. CRM Relationships service consumes the event and creates follow-up tasks.
5. Task list or company/deal detail view refreshes or refetches.
6. New task becomes visible.

### Flow D: Log Activity

1. User opens a company or deal detail page.
2. User clicks `Log Activity`.
3. User selects type and enters details.
4. User submits the form.
5. Activity appears in the company or deal history.

### Flow E: Complete Follow-Up Work

1. User opens the task list.
2. User filters to pending tasks.
3. User opens a task or updates it inline.
4. User marks the task complete.
5. Updated task state is reflected in the task list and related company/deal views.

## 6. Eventual Consistency UX

The frontend must clearly handle asynchronous behavior.

Expected UX behavior:

- deal status changes should be reflected immediately after the mutation succeeds
- downstream task creation may not appear instantly
- the UI should either poll, refetch on interval, or refetch after a short delay
- the UI should show a non-blocking message such as `Follow-up tasks may appear shortly`

## 7. Minimum Initial UI

A minimal but complete initial implementation can ship with these screens:

- `Login`
- `Company List`
- `Company Detail`
- `Create/Edit Company`
- `Create/Edit Contact`
- `Deal List`
- `Deal Detail`
- `Create Deal`
- `Task List`

Activity and task create/edit forms may be implemented as modals or inline forms instead of standalone pages.

## 8. Recommended Backend Operations Needed by the Frontend

Likely GraphQL queries:

- `me`
- `companies`
- `company(id)`
- `deals`
- `deal(id)`
- `tasks`

Likely GraphQL mutations:

- `createCompany`
- `updateCompany`
- `createContact`
- `updateContact`
- `createDeal`
- `updateDealStatus`
- `createActivity`
- `createTask`
- `updateTask`
