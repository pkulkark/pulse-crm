# SampleCRM Testing Guide

This document is the common verification reference for the repo.

The goal is simple:

- every command defined in `project.json` files should work
- the runtime stack should start cleanly
- the currently implemented live endpoints should behave correctly

This guide is intentionally not phase-by-phase. It is organized around the commands and checks that should remain valid as the system evolves.

## Baseline Setup

Install the repo dependencies first:

```bash
npm install
python3 -m venv .venv
./.venv/bin/pip install -r apps/identity_service/requirements.txt
./.venv/bin/pip install -r apps/crm_relationships_service/requirements.txt
./.venv/bin/pip install -r apps/deals_service/requirements.txt
```

Useful local endpoints:

- frontend: `http://localhost:3000`
- gateway GraphQL: `http://localhost:4000/`
- gateway health: `http://localhost:4000/health`
- identity service health: `http://localhost:8101/health/`
- CRM relationships service health: `http://localhost:8002/health/`
- deals service health: `http://localhost:8003/health/`

## Rule

All commands defined in these files should work:

- [project.json](/Users/poojakulkarni/SampleCRM/project.json)
- [apps/frontend/project.json](/Users/poojakulkarni/SampleCRM/apps/frontend/project.json)
- [apps/gateway/project.json](/Users/poojakulkarni/SampleCRM/apps/gateway/project.json)
- [apps/identity_service/project.json](/Users/poojakulkarni/SampleCRM/apps/identity_service/project.json)
- [apps/crm_relationships_service/project.json](/Users/poojakulkarni/SampleCRM/apps/crm_relationships_service/project.json)
- [apps/deals_service/project.json](/Users/poojakulkarni/SampleCRM/apps/deals_service/project.json)

For one-shot targets like `build`, `lint`, and `test`, success means the command exits cleanly.

For long-running `serve` targets, success means:

- the process starts successfully
- it binds the expected port
- the service responds to a basic smoke check

## Root Commands

These are the top-level repo entrypoints:

```bash
npm run build
npm run lint
npm run test
```

If `nx run-many` is flaky in a local environment, verify the underlying project targets directly as well.

## Workspace Commands

Current workspace-level checks behind [project.json](/Users/poojakulkarni/SampleCRM/project.json):

```bash
node -e "const fs=require('node:fs'); const required=['.editorconfig','.env.example','docker-compose.yml','eslint.config.mjs','nx.json','package.json','ruff.toml']; for (const file of required) { if (!fs.existsSync(file)) { throw new Error('Missing required file: ' + file); } } JSON.parse(fs.readFileSync('package.json','utf8')); JSON.parse(fs.readFileSync('nx.json','utf8')); JSON.parse(fs.readFileSync('project.json','utf8')); const compose=fs.readFileSync('docker-compose.yml','utf8'); for (const marker of ['frontend:','gateway:','identity-service:','crm-relationships-service:','deals-service:','identity-db:','crm-db:','deals-db:','kafka:']) { if (!compose.includes(marker)) { throw new Error('Missing compose service definition: ' + marker); } }"
python3 -m unittest discover -s tests -p 'test_*.py'
```

Expected result:

- required workspace files exist
- config JSON parses successfully
- compose contains the expected service definitions
- root Python tests pass

## Frontend Commands

Commands behind [apps/frontend/project.json](/Users/poojakulkarni/SampleCRM/apps/frontend/project.json):

```bash
npm run build --workspace @samplecrm/frontend
npm run lint --workspace @samplecrm/frontend
node -e "const fs=require('node:fs'); const required=['apps/frontend/package.json','apps/frontend/project.json','apps/frontend/index.html','apps/frontend/src/App.jsx','apps/frontend/src/main.jsx','apps/frontend/src/styles.css','apps/frontend/vite.config.js']; for (const file of required) { if (!fs.existsSync(file)) { throw new Error('Missing required file: ' + file); } } const appSource=fs.readFileSync('apps/frontend/src/App.jsx','utf8'); if (!appSource.includes('Sample Workspace')) { throw new Error('Frontend placeholder copy is missing'); } if (!appSource.includes('Gateway')) { throw new Error('Frontend service list is missing gateway content'); }"
```

Serve check:

```bash
npm run dev --workspace @samplecrm/frontend -- --host 0.0.0.0 --port 3000
curl http://127.0.0.1:3000
```

Expected result:

- frontend production build completes
- frontend lint passes
- the dev server starts on `3000`
- `curl` returns the HTML shell

## Gateway Commands

Commands behind [apps/gateway/project.json](/Users/poojakulkarni/SampleCRM/apps/gateway/project.json):

```bash
node --check apps/gateway/src/server.mjs
npm run lint --workspace @samplecrm/gateway
node --test apps/gateway/src/server.test.mjs
```

Serve check:

```bash
PORT=4000 npm run start --workspace @samplecrm/gateway
curl http://127.0.0.1:4000/health
```

Expected result:

- syntax check passes
- lint passes
- gateway tests pass
- the server starts on `4000`
- `/health` returns gateway status JSON

## Django Service Commands

The three Django services should all support:

- `build`
- `lint`
- `test`
- `serve`

### Identity Service

Commands behind [apps/identity_service/project.json](/Users/poojakulkarni/SampleCRM/apps/identity_service/project.json):

```bash
cd apps/identity_service && PYTHONPYCACHEPREFIX=/tmp/samplecrm-pyc ../../.venv/bin/python -m compileall -q . && ../../.venv/bin/python manage.py check
cd apps/identity_service && ../../.venv/bin/python manage.py test
cd apps/identity_service && DB_HOST=127.0.0.1 DB_PORT=5433 ../../.venv/bin/python manage.py runserver 0.0.0.0:8101
```

Smoke check:

```bash
curl http://127.0.0.1:8101/health/
```

### CRM Relationships Service

Commands behind [apps/crm_relationships_service/project.json](/Users/poojakulkarni/SampleCRM/apps/crm_relationships_service/project.json):

```bash
cd apps/crm_relationships_service && PYTHONPYCACHEPREFIX=/tmp/samplecrm-pyc ../../.venv/bin/python -m compileall -q . && ../../.venv/bin/python manage.py check
cd apps/crm_relationships_service && ../../.venv/bin/python manage.py test
cd apps/crm_relationships_service && DB_HOST=127.0.0.1 DB_PORT=5434 ../../.venv/bin/python manage.py runserver 0.0.0.0:8002
```

Smoke check:

```bash
curl http://127.0.0.1:8002/health/
```

### Deals Service

Commands behind [apps/deals_service/project.json](/Users/poojakulkarni/SampleCRM/apps/deals_service/project.json):

```bash
cd apps/deals_service && PYTHONPYCACHEPREFIX=/tmp/samplecrm-pyc ../../.venv/bin/python -m compileall -q . && ../../.venv/bin/python manage.py check
cd apps/deals_service && ../../.venv/bin/python manage.py test
cd apps/deals_service && DB_HOST=127.0.0.1 DB_PORT=5435 ../../.venv/bin/python manage.py runserver 0.0.0.0:8003
```

Smoke check:

```bash
curl http://127.0.0.1:8003/health/
```

Expected result for all Django services:

- compile/check passes
- test suite passes
- dev server starts on its assigned port
- health endpoint responds

## Docker Compose Checks

The containerized runtime should also work:

```bash
docker compose up --build
docker compose ps
curl http://localhost:4000/health
curl http://localhost:8101/health/
curl http://localhost:8002/health/
curl http://localhost:8003/health/
```

Useful runtime checks:

```bash
docker compose logs gateway --tail 100
docker compose logs identity-service --tail 100
docker compose logs crm-relationships-service --tail 100
docker compose logs deals-service --tail 100
docker compose logs kafka --tail 100
```

Expected result:

- containers start cleanly
- health checks go green
- logs are sufficient to diagnose startup and cross-service issues

## Live Gateway Smoke Checks

These are the main live endpoint checks that should continue to work as the system grows.

Current known users:

- `admin@example.com` / `secret`
- `manager@example.com` / `secret`

### Health

```bash
curl http://localhost:4000/health
```

### Login

```bash
curl http://localhost:4000/ \
  -H 'content-type: application/json' \
  -d '{"query":"mutation { login(input: { email: \"admin@example.com\", password: \"secret\" }) { token user { id email role companyId } } }"}'
```

### Current User

```bash
curl http://localhost:4000/ \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer <TOKEN>' \
  -d '{"query":"query { me { id email role companyId } }"}'
```

### Invalid Token

```bash
curl http://localhost:4000/ \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer invalid-token' \
  -d '{"query":"query { me { id } }"}'
```

### Downstream Context Propagation

```bash
curl http://localhost:4000/ \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer <TOKEN>' \
  -d '{"query":"query { serviceHealth { service status requestContext { companyId correlationId userId userRole } } }"}'
```

Expected result:

- login returns a token and user object
- `me` returns the authenticated user
- invalid tokens fail with `401`
- downstream request context includes trusted `userId`, `userRole`, and `companyId`

## Quick Regression Checklist

Use this before considering a change safe:

1. The root commands still run:
   - `npm run build`
   - `npm run lint`
   - `npm run test`
2. Every command defined in `project.json` files still works.
3. Docker Compose still boots cleanly.
4. Gateway `/health` still responds.
5. Gateway `login` and `me` still work.
6. Gateway tests still pass.
7. The changed service’s local `serve` command still starts successfully.
