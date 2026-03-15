# Phase 0: Repository and Workspace Setup

## Objective

Establish the project structure, local runtime, and developer workflow so later phases can be added without reworking the foundation.

## Scope

- minimal Nx workspace setup
- service/app directory layout
- base Docker Compose wiring
- environment configuration conventions
- linting and formatting setup
- placeholder app startup for all planned services

## Engineering Standards

- code quality must be industry-standard and production-level from the first commit
- keep the workspace structure simple and explicit
- do not overengineer the repo layout or invent abstractions before they are needed
- avoid overly defensive coding in setup scripts; fail clearly on invalid configuration instead
- prefer boring, well-understood tooling defaults unless there is a clear reason to diverge
- keep Django services idiomatic; `Nx` is only the workspace/task runner layer

## Work Breakdown

1. Create a minimal Nx workspace and define application boundaries for:
   - frontend
   - gateway
   - identity/access service
   - CRM relationships service
   - deals service
2. Keep each backend service as a plain Django project with normal Django/Python layout and tooling.
3. Create a consistent directory structure for apps, shared config, and local scripts.
4. Add formatting, linting, and base editor config.
5. Create `.env.example` files and document expected environment variables.
6. Create a base `docker-compose.yml` with placeholder services, databases, and Kafka.
7. Add health endpoints or placeholder startup commands for each service.

## Recommended Repository Layout

The repository layout should keep Django idiomatic and use `Nx` only as a thin workspace layer:

```text
SampleCRM/
  apps/
    frontend/
      src/
      package.json
    gateway/
      src/
      package.json
    identity_service/
      manage.py
      pyproject.toml
      requirements.txt
      identity_service/
      apps/
    crm_relationships_service/
      manage.py
      pyproject.toml
      requirements.txt
      crm_relationships_service/
      apps/
    deals_service/
      manage.py
      pyproject.toml
      requirements.txt
      deals_service/
      apps/
  docs/
  infra/
    docker/
    compose/
  scripts/
  .env.example
  docker-compose.yml
  nx.json
  package.json
```

### Layout Notes

- `apps/frontend` contains the React application.
- `apps/gateway` contains the GraphQL gateway.
- each backend service lives under its own folder in `apps/` and remains a normal Django project
- each Django service should keep its own `manage.py`, dependency definition, settings, and migrations
- service-specific Django apps should remain inside the service folder rather than being prematurely shared
- `infra/` should contain Docker-related helpers or local runtime files, not business code
- `scripts/` should contain simple developer utilities only

## Why This Layout

This structure satisfies the specification without forcing Django into an unnatural monorepo shape.

It preserves:

- standard Django commands such as migrations, test runs, and local management commands
- clear per-service ownership
- simple Docker Compose wiring
- a clean place for `Nx` to orchestrate tasks without becoming the backend framework

## Deliverables

- workspace committed
- all planned apps present in the repo
- Docker Compose starts the full system skeleton
- local development conventions documented
- Django services remain standard Django applications rather than custom Nx-style backends

## Acceptance Criteria

- `docker compose up --build` starts successfully
- each service container starts and reports healthy or returns a placeholder response
- repo structure is clear enough that later phases can be added without renaming or reorganizing the workspace
- the Nx layer does not interfere with normal Django development commands, migrations, or app layout

## Out of Scope

- real business models
- production authentication
- GraphQL federation behavior beyond placeholders

## Recommended Verification

- start the full stack from a clean checkout
- verify each container is reachable
- verify env loading works as documented
- verify Django management commands run normally inside each service
