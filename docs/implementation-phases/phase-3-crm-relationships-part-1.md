# Phase 3: CRM Relationships Service, Part 1

## Objective

Implement the company and contact foundation that anchors the rest of the CRM domain.

## Scope

- `Company`
- `Contact`
- parent-child company hierarchy
- admin-only company/contact mutations
- gateway-exposed company and contact reads

## Engineering Standards

- code quality must be industry-standard and production-level
- model the company hierarchy clearly and keep constraints close to the model and mutation boundaries
- do not overengineer hierarchy traversal or generic metadata systems
- avoid overly defensive coding that spreads the same validation across serializers, resolvers, and models without a clear reason
- keep read and write ownership obvious inside the service

## Work Breakdown

1. Implement `Company` and `Contact` models and migrations.
2. Add constraints for parent-child hierarchy integrity.
3. Implement create and update mutations for companies and contacts.
4. Implement list and detail queries for companies and contacts.
5. Enforce admin-only write access for company/contact mutations.
6. Expose fields needed by downstream federation.
7. Add tests for hierarchy validation and permission checks.

## Deliverables

- company and contact persistence
- hierarchical company data
- admin-only company/contact writes
- gateway query support for company and contact data

## Acceptance Criteria

- admin can create a parent company and a child company
- admin can create contacts under a company
- non-admin users cannot create or edit companies or contacts
- company list and company detail data resolve through the gateway

## Out of Scope

- tasks
- activities
- complex hierarchy reporting

## Recommended Verification

- create parent and child companies
- verify company detail shows hierarchy
- create contacts and verify they are scoped to one company

