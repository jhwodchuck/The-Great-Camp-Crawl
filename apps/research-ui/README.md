# Research UI – Setup & Development Guide

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

## Database Schema

SQLite database stored at `data/staging/research_ui.db` (configurable via `RESEARCH_UI_DB` env var).

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
| `RESEARCH_UI_DB` | `data/staging/research_ui.db` | Path to SQLite database |
| `RESEARCH_UI_SECRET` | `dev-secret-change-in-production-please` | JWT signing secret |
| `TOKEN_EXPIRE_MINUTES` | `480` | JWT expiry (8 hours) |

⚠️ **Always set `RESEARCH_UI_SECRET` to a random secret in production.**

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
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## Running Tests

Backend tests use pytest with a real SQLite temp file:

```bash
# From the repo root
python -m pytest tests/research_ui/ -v
```

## Promoted Artifacts

When a parent approves and promotes a contribution, a JSON file is written to:

```
data/staging/contributions/contrib-{id}-{slug}.json
```

This file uses the same `venue_candidate` schema as the existing Python discovery pipeline and can be ingested via `scripts/ingest_discovery_reports.py`.

## Security Notes

- Children can **never** edit raw Markdown dossiers or access GitHub directly
- All child contributions require parent approval before export
- Passwords are hashed with bcrypt
- JWT tokens expire after 8 hours
- Children can only see and edit their own contributions
- API enforces role-based access at every endpoint

## Folder Structure for Artifacts

```
data/staging/contributions/   # promoted approved contributions (JSON)
data/staging/review-queue/    # (reserved for future use)
data/staging/research_ui.db   # SQLite database
```
