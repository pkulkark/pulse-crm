# PulseCRM

PulseCRM is a small event-driven CRM delivered as a monorepo:

- `apps/frontend`: React UI
- `apps/gateway`: Apollo GraphQL gateway
- `apps/identity_service`: Django identity/auth service
- `apps/crm_relationships_service`: Django company, contact, task, and activity service
- `apps/deals_service`: Django deals service
- Kafka: async workflow for deal status changes

The main user-facing flow is:

1. sign in through the gateway-backed frontend
2. manage companies and contacts
3. create and update deals
4. log activities
5. create manual tasks or let Kafka create a follow-up task when a deal moves to `QUALIFIED`

## Local Setup

### Prerequisites

- Docker with Compose
- Node.js with npm
- Python 3

### From a Clean Checkout

1. Install Node dependencies:

   ```bash
   npm install
   ```

2. Create a virtualenv for the Django checks:

   ```bash
   python3 -m venv .venv
   ```

3. Install Python dependencies for the three Django services:

   ```bash
   ./.venv/bin/pip install -r apps/identity_service/requirements.txt
   ./.venv/bin/pip install -r apps/crm_relationships_service/requirements.txt
   ./.venv/bin/pip install -r apps/deals_service/requirements.txt
   ```

4. Start the full stack:

   ```bash
   docker compose up --build
   ```

The default Compose setup is enough for a first run. You do not need a local `.env` file unless you want to override ports. If you do copy `.env.example` to `.env`, note that it changes the identity-service host port from `8101` to `8001`.

### Service URLs

These URLs assume the default Compose ports with no local `.env` override:

- Main application: `http://localhost:3000`
- Gateway GraphQL: `http://localhost:4000/`
- Gateway health: `http://localhost:4000/health`
- Identity service health: `http://localhost:8101/health/`
- CRM relationships service health: `http://localhost:8002/health/`
- Deals service health: `http://localhost:8003/health/`

Open `http://localhost:3000` for the main application. The other URLs are useful for smoke checks and debugging.

### Demo Users

The repo seeds three users through Django migrations:

- `admin@example.com` / `secret`
- `manager@example.com` / `secret`
- `salesrep@example.com` / `secret`

The CRM UI does not include user management yet. Today the repo works like this:

- the three demo users above are created automatically by migrations
- additional users are currently a Django-admin-or-management-command concern rather than a product UI flow
- in this repo, the wired path today is Django management commands in the identity service
- a fuller user-management UI is future work

Example commands:

```bash
docker compose exec identity-service python manage.py createsuperuser
```

```bash
docker compose exec identity-service python manage.py shell -c "from apps.users.models import User, UserRole; import uuid; User.objects.create_user(email='new.manager@example.com', password='secret', name='New Manager', company_id=uuid.UUID('11111111-1111-1111-1111-111111111111'), role=UserRole.MANAGER)"
```

The implementation currently wires the management-command path. Django admin is not enabled in this repo yet.

## Architecture Summary

- The frontend talks only to the GraphQL gateway.
- The gateway federates the three backend services.
- Each Django service owns its own data.
- Kafka is used for one async workflow: when a deal status changes to `QUALIFIED`, the CRM relationships service creates a follow-up task.

The higher-level design is documented in [docs/architecture.md](docs/architecture.md), [docs/frontend.md](docs/frontend.md), and [docs/implementation-plan.md](docs/implementation-plan.md).

## Automated Checks

Run the verified local checks with:

```bash
NX_DAEMON=false npm run build
NX_DAEMON=false npm run lint
NX_DAEMON=false npm run test
```

In this environment the underlying project targets passed, but plain `npm run build|lint|test` hit an Nx daemon crash until `NX_DAEMON=false` was used. The detailed verification commands live in [docs/testing-guide.md](docs/testing-guide.md).

## Browser Walkthrough

This is the clearest order for exercising the implemented UI from a fresh run.

### 1. Admin setup flow

1. Open `http://localhost:3000`.
2. Sign in as `admin@example.com`.
3. In `Companies`, create a company.
4. Open that company and add a contact.

You can skip this admin setup and use the seeded `Sample Industries` company if you only want to test the manager workflow. The admin setup is useful because company and contact editing are admin-only in the current implementation.

### 2. Manager CRM flow

1. Sign out.
2. Sign in as `manager@example.com`.
3. In `Companies`, select the company you want to work with.
4. Click `Create deal`.
5. Pick the company, optionally pick the contact, and create the deal.
6. From the deal detail view, click `Log activity` and save a note, call, meeting, or email.
7. In the same deal detail view, change the status from `NEW` to `QUALIFIED`.
8. Wait a few seconds for the Kafka-driven follow-up task to appear in the deal detail panel.
9. Open `Tasks`.
10. Leave the scope on `Assigned to me` and confirm the new `Schedule follow-up` task is present.
11. Click `Complete` to mark the task done.

### 3. Optional role check

Sign in as `salesrep@example.com` if you want to compare the restricted UI:

- company and contact edit actions are not available
- task creation is not available
- assigned task completion is available

## Improvement Points

- User management is incomplete. The app ships seeded users, but there is no user-management UI and no Django admin wiring in the repo.
- Task assignees are not fully human-readable in every case. The task table shows `You` for the current user, but other assignees still fall back to a short raw user identifier.
- The system has creation and update flows, but no delete/archive flows for CRM records.
- Access control is role-based and globally scoped across CRM data. There is no per-team or per-company tenancy model yet.
- The async workflow is intentionally narrow: only `deal.status_changed -> follow-up task` is implemented.
- The repo is optimized for local Compose verification, not production deployment automation.

## Shutdown

Stop the local stack with:

```bash
docker compose down
```
