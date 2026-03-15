# SampleCRM

Phase 0 establishes a minimal monorepo foundation for the CRM system.

## Workspace approach

- `Nx` is the workspace and task runner layer only.
- `apps/frontend` is a React application.
- `apps/gateway` is the gateway placeholder service.
- each backend service remains an idiomatic Django project under `apps/`

## Repository layout

```text
apps/
  frontend/
  gateway/
  identity_service/
  crm_relationships_service/
  deals_service/
infra/
  docker/
  compose/
scripts/
tests/
```

## Local development

1. Copy `.env.example` to `.env`.
2. Install Node dependencies with `npm install`.
3. Install Python dependencies for any Django service you want to run locally, for example:
   `python3 -m venv .venv && ./.venv/bin/pip install -r apps/identity_service/requirements.txt`
4. Run workspace checks with `npm run lint` and `npm run test`.
5. Start the full stack with `docker compose up --build`.

## Service endpoints

- frontend: `http://localhost:3000`
- gateway health: `http://localhost:4000/health`
- gateway GraphQL: `http://localhost:4000/`
- identity service: `http://localhost:8101/health/`
- CRM relationships service: `http://localhost:8002/health/`
- deals service: `http://localhost:8003/health/`

## Environment conventions

- root `.env` holds compose-level ports and shared local defaults
- each app also includes a local `.env.example` documenting app-specific settings
- Django services use normal `manage.py` commands and service-local settings modules
