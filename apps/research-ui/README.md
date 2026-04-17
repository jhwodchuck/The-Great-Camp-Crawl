# Research UI – Setup, Deployment & Operations Guide

A child-friendly camp research collaboration app built with FastAPI (backend) and Next.js (frontend).

## Architecture Overview

```
apps/research-ui/
├── backend/          # FastAPI + SQLite
│   ├── main.py
│   ├── database.py   # SQLAlchemy engine (SQLite)
│   ├── models.py     # ORM models
│   ├── schemas.py    # Pydantic schemas
│   ├── auth.py       # JWT authentication
│   └── routers/      # API route handlers
│       ├── auth.py
│       ├── missions.py
│       ├── contributions.py
│       ├── evidence.py
│       ├── answers.py
│       ├── reviews.py
│       └── export.py
└── frontend/         # Next.js 16 + Tailwind CSS
    ├── app/
    │   ├── login/
    │   ├── register/
    │   ├── dashboard/
    │   ├── missions/       # browse + [id]/ + new/
    │   ├── contributions/  # list + [id]/
    │   └── review/         # queue + [id]/
    ├── lib/
    │   ├── api.ts          # typed API client
    │   └── auth.tsx        # React auth context
    └── components/
        └── NavBar.tsx
```

## Deployment Architecture

This app is now structured to deploy as a single Vercel project with two services:

- `web` → `apps/research-ui/frontend` (Next.js)
- `api` → `apps/research-ui/backend/main.py` (FastAPI) mounted at `/backend`

That means the browser stays on one domain, and the frontend talks to the backend through `/backend/api/...`.

## Database Schema

Local development can use SQLite at `data/staging/research_ui.db`.

Production on Vercel must use Postgres via `RESEARCH_UI_DATABASE_URL` or Vercel Postgres env vars. SQLite is intentionally rejected on Vercel because it does not preserve child edits reliably across serverless instances.

| Table | Key columns |
|---|---|
| `users` | id, username, display_name, password_hash, role (parent/child) |
| `missions` | id, title, description, region, country, program_family, created_by |
| `contributions` | id, mission_id, contributor_id, camp_name, website_url, status, … |
| `evidence` | id, contribution_id, url, snippet, capture_notes |
| `answers` | id, contribution_id, question_key, answer_text |
| `reviews` | id, contribution_id, reviewer_id, action, notes |

### Contribution Statuses

```
draft → submitted → under_review → approved → (promoted to staging)
                                → rejected
                                → changes_requested → (child edits) → submitted
```

## API Routes

| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/register` | anyone |
| POST | `/api/auth/login` | anyone |
| GET  | `/api/auth/me` | authenticated |
| GET/POST | `/api/missions/` | GET: all; POST: parent only |
| GET/PATCH/DELETE | `/api/missions/{id}` | GET: all; PATCH/DELETE: parent |
| GET/POST | `/api/contributions/` | child sees own; parent sees all |
| GET/PATCH | `/api/contributions/{id}` | owner or parent |
| POST | `/api/contributions/{id}/submit` | owner |
| GET/POST | `/api/contributions/{id}/evidence/` | owner or parent |
| DELETE | `/api/contributions/{id}/evidence/{eid}` | owner |
| GET | `/api/contributions/{id}/answers/questions` | all |
| GET/PUT | `/api/contributions/{id}/answers/` | owner or parent |
| GET | `/api/reviews/queue` | parent only |
| POST | `/api/reviews/{id}` | parent only |
| GET | `/api/reviews/{id}` | parent only |
| POST | `/api/export/{id}` | parent only (approved only) |
| GET | `/api/export/preview/{id}` | parent only |

## Frontend Screens

| Screen | Path | Role |
|---|---|---|
| Landing / redirect | `/` | all |
| Login | `/login` | all |
| Register | `/register` | all |
| Dashboard | `/dashboard` | all (role-adaptive) |
| Browse Missions | `/missions` | all |
| Mission Detail + Add Camp | `/missions/[id]` | all (add: child) |
| New Mission | `/missions/new` | parent |
| My Contributions | `/contributions` | child |
| Contribution Detail + Edit | `/contributions/[id]` | owner + parent |
| Review Queue | `/review` | parent |
| Review a Contribution | `/review/[id]` | parent |

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend Setup

```bash
cd apps/research-ui/backend

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000.  
Interactive docs: http://localhost:8000/docs

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RESEARCH_UI_DB` | `data/staging/research_ui.db` | Local SQLite path for development only |
| `RESEARCH_UI_DATABASE_URL` | unset | Production database URL (preferred on Vercel) |
| `RESEARCH_UI_SECRET` | `dev-secret-change-in-production-please` | JWT signing secret |
| `TOKEN_EXPIRE_MINUTES` | `480` | JWT expiry (8 hours) |
| `RESEARCH_UI_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed browser origins for local development |
| `RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME` | unset | Optional pre-created parent username |
| `RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD` | unset | Optional pre-created parent password |
| `RESEARCH_UI_BOOTSTRAP_PARENT_DISPLAY_NAME` | `Parent` | Optional pre-created parent display name |
| `RESEARCH_UI_PARENT_INVITE_CODE` | unset | Optional invite code required for parent self-registration |
| `RESEARCH_UI_ALLOW_UNINVITED_FIRST_PARENT` | `true` locally, `false` in production | Whether the first parent can self-register without an invite |
| `RESEARCH_UI_ENABLE_FILE_EXPORTS` | `true` locally, `false` on Vercel | Mirror approved exports to JSON files when the filesystem is writable |
| `RESEARCH_UI_EXPORT_DIR` | `data/staging/contributions` | Filesystem export mirror path |

`apps/research-ui/.env.example` contains a deployment-safe template.

## Frontend Setup

```bash
cd apps/research-ui/frontend

# Install dependencies
npm install

# Run the development server
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

The app will be available at http://localhost:3000.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` locally, `/backend` in production fallback | Backend API base URL |

## Running Tests

Backend tests use pytest with a real SQLite temp file:

```bash
# From the repo root
python -m pytest tests/research_ui/ -v
```

## Promoted Artifacts

When a parent approves and promotes a contribution, the export is always stored in the database and can optionally be mirrored to a JSON file in writable environments.

Local file mirror path:

```
data/staging/contributions/contrib-{id}-{slug}.json
```

The payload uses the same `venue_candidate` schema as the existing Python discovery pipeline and can be ingested via `scripts/ingest_discovery_reports.py`.

## Security Notes

- Children can **never** edit raw Markdown dossiers or access GitHub directly
- All child contributions require parent approval before export
- Passwords are hashed with bcrypt
- JWT tokens expire after 8 hours
- Children can only see and edit their own contributions
- API enforces role-based access at every endpoint
- Public parent registration is no longer open by default in production
- Vercel deployments require an explicit database, JWT secret, and parent bootstrap strategy before startup succeeds

## GitHub Actions

Two workflows are included:

- `Research UI CI` runs backend tests plus frontend lint/build on pull requests and pushes to `main`
- `Research UI Vercel Deploy` creates preview deployments for pull requests and production deployments from `main`

Set these GitHub Actions secrets before enabling deploys:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

## Vercel Setup

1. Create a Vercel project from this repository.
2. Attach Vercel Postgres or provide `RESEARCH_UI_DATABASE_URL`.
3. Add required env vars:
   - `RESEARCH_UI_SECRET`
   - either `RESEARCH_UI_BOOTSTRAP_PARENT_USERNAME` + `RESEARCH_UI_BOOTSTRAP_PARENT_PASSWORD`
   - or `RESEARCH_UI_PARENT_INVITE_CODE`
4. Keep the Vercel project rooted at the repository root so `vercel.json` can route both services.
5. Copy the project `orgId` and `projectId` into GitHub Actions secrets for deploy automation.

## Folder Structure for Artifacts

```
data/staging/contributions/   # promoted approved contributions (JSON)
data/staging/review-queue/    # (reserved for future use)
data/staging/research_ui.db   # SQLite database
```
