# IntelliWatch

A multi-tenant competitive intelligence tool. Each user adds competitors to
track, and once a week IntelliWatch pulls fresh signals from six free data
sources, deduplicates them, and uses an LLM to write a digest brief covering
engineering direction, hiring signals, sentiment, and what changed since last
week — delivered both in-app and by email.

## What it does

1. **Add a competitor** — give it a name plus whichever sources apply (GitHub
   repo, Hacker News query, YouTube channel, job board, pricing page URL,
   news query, blog RSS).
2. **Run** (manually, or automatically every week) — six agents fan out in
   parallel to pull raw activity from each configured source.
3. **Extract** — GPT-4o-mini turns raw, noisy signals into structured
   `(title, summary, category, date)` records.
4. **Deduplicate** — text-embedding similarity + union-find clustering groups
   near-duplicate signals from different sources into one cluster.
5. **Synthesize** — Claude Sonnet writes a markdown brief from the clusters,
   diffing against last week's brief to highlight what's new.
6. **Digest email** — once a week, every user gets one email summarizing all
   their competitors' latest briefs.

Users can optionally supply their own OpenAI/Anthropic API keys (BYOK),
encrypted at rest, so LLM usage is billed to their own account instead of the
app owner's.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI |
| Agent orchestration | LangGraph + LangChain |
| LLMs | Claude Sonnet 4.6 (brief synthesis), GPT-4o-mini (extraction/dedup) |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Database | MongoDB Atlas |
| Auth | Auth.js (NextAuth) + MongoDB adapter, JWT sessions |
| Email | Brevo |
| Containerization | Docker + docker-compose (local dev) |
| Deploy | Render (backend) + Vercel (frontend) |
| Scheduling | GitHub Actions cron -> `/internal/run-all` and `/internal/send-digest` |

## Data sources

Six independent modules, each wrapped as a tool on one FastMCP server and run
in-process by the backend:

| Module | Source | API |
|---|---|---|
| `github-mcp` | Repo activity, releases | GitHub REST API |
| `hn-mcp` | Hacker News mentions | Algolia Search API |
| `youtube-mcp` | Channel video uploads | YouTube channel RSS |
| `jobs-mcp` | Job postings (optional) | Greenhouse / Lever public APIs |
| `scraper-mcp` | Pricing page diffs | BeautifulSoup (fail-soft) |
| `news-mcp` | General press | Google News RSS + optional blog RSS |

## Project structure

```
backend/
  app/
    main.py          # FastAPI app, /health
    auth.py           # JWT verification dependency
    db.py             # MongoDB connection
    crypto.py          # Fernet encryption for per-user API keys
    api_keys.py        # decrypt/merge per-user OpenAI/Anthropic keys
    digest.py           # weekly digest email rendering
    models.py            # Pydantic schemas
    mcp/                  # 6 MCP-pattern data source modules + FastMCP server
    graph/                # LangGraph: supervisor -> sub-agents -> extract -> dedup -> brief
    routers/              # competitors CRUD, /run, /briefs, /internal/*, /me/api-keys
  tests/                  # standalone end-to-end test scripts, one per phase
  Dockerfile
  requirements.txt

frontend/
  src/
    app/
      page.jsx            # dashboard (list competitors)
      competitors/         # add competitor, competitor detail + run + briefs
      settings/             # BYOK API key management
      login/ signup/          # Auth.js credential pages
      api/                    # NextAuth route handlers
    lib/                       # apiFetch helper (forwards session as bearer token)
  Dockerfile

docker-compose.yml    # local dev: backend + frontend
.github/workflows/    # weekly cron -> /internal/run-all, /internal/send-digest
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for how data flows through the system,
and [.env.example](.env.example) for required configuration.

## Local development

Requires Docker.

```bash
git clone <this repo>
cd intelliwatch
cp .env.example .env        # fill in MONGODB_URI, AUTH_SECRET, API keys, etc.
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Frontend: http://localhost:3000

The frontend also needs its own `frontend/.env.local` with `MONGODB_URI`,
`AUTH_SECRET` (same values as the root `.env`, used by Auth.js), and
`BACKEND_URL` (set to `http://localhost:8000` for non-Docker dev — Docker
Compose overrides this to `http://backend:8000` automatically).

## Testing

Each backend phase has a standalone test script in `backend/tests/` that
exercises that part of the pipeline end-to-end against the real MongoDB
Atlas database and real external APIs — run from inside the backend
container or a local virtualenv with `backend/requirements.txt` installed:

```bash
cd backend
python -m tests.test_github_mcp   # or any other tests.test_* module
```
