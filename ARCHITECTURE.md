# Architecture

## High-level flow

```
                         Weekly cron (GitHub Actions)
                                    |
                                    v
                        POST /internal/run-all  (X-Internal-Secret)
                                    |
                    for each (user, competitor) pair
                                    v
+--------------------------------------------------------------------+
|                          LangGraph pipeline                        |
|                                                                      |
|   supervisor                                                        |
|       |--> github_agent  --\                                       |
|       |--> hn_agent       --\                                       |
|       |--> youtube_agent   ---> save_to_mongo --> raw_signals       |
|       |--> jobs_agent      --/        |                             |
|       |--> scraper_agent  --/         v                             |
|       |--> news_agent     -/    extract_agent (GPT-4o-mini)         |
|                                        |                             |
|                                        v                             |
|                                  extracted_signals                   |
|                                        |                             |
|                                        v                             |
|                              dedup_agent (embeddings +               |
|                                union-find clustering)                |
|                                        |                             |
|                                        v                             |
|                                 signal_clusters                      |
|                                        |                             |
|                                        v                             |
|                          brief_writer (Claude Sonnet,                |
|                          diffs against last week's brief)            |
|                                        |                             |
|                                        v                             |
|                                     briefs                           |
+--------------------------------------------------------------------+
                                    |
                                    v
                  POST /internal/send-digest  (X-Internal-Secret)
                                    |
                       per user: aggregate latest brief per
                       competitor -> one digest email (Brevo)
```

The same graph runs synchronously when a user clicks "Run now" on a
competitor (`POST /competitors/{id}/run`) — the scheduled path and the
manual path share one implementation.

## Backend (`backend/app`)

- **`main.py`** — FastAPI app instance, `/health`, mounts routers.
- **`auth.py`** — `get_current_user` dependency: verifies the JWT (HS256,
  shared `AUTH_SECRET`) sent as a bearer token, returns `{user_id, email}`.
  JWTs are stateless — no session table, so a deleted user's still-valid
  token simply finds no data.
- **`db.py`** — Motor (async MongoDB) client, shared across requests.
- **`crypto.py`** — Fernet symmetric encryption (`ENCRYPTION_KEY`) for
  per-user API keys at rest.
- **`api_keys.py`** — `get_user_api_keys(db, user_id)` decrypts and returns
  whichever of the user's OpenAI/Anthropic keys are set (or `None`).
- **`models.py`** — Pydantic request/response schemas, including
  `exclude_unset`-aware partial-update models for settings.
- **`digest.py`** — renders the weekly digest email (HTML) from each user's
  latest briefs.

### `mcp/` — data source modules

Each module (`github_mcp.py`, `hn_mcp.py`, `youtube_mcp.py`, `jobs_mcp.py`,
`scraper_mcp.py`, `news_mcp.py`) implements one source as a function
returning a list of `Signal` objects (`schemas.py`). `server.py` wraps all
six as tools on a single **FastMCP** server, run in-process (no separate
deployed MCP services) — the LangGraph agents call them via an in-memory
`Client(mcp)`. Each module is fail-soft: a source erroring (rate limit, dead
page) returns an empty list rather than failing the whole run.

### `graph/` — LangGraph pipeline

- **`state.py`** — `GraphState` TypedDict: competitor config, accumulated
  signals (via `operator.add` reducer for parallel fan-in), and optional
  per-user `openai_api_key` / `anthropic_api_key`.
- **`nodes.py`** — supervisor + one node per data source (parallel fan-out),
  `save_to_mongo`.
- **`extraction.py`** — `extract_agent`: caps raw signals per source (15),
  calls GPT-4o-mini with `client.beta.chat.completions.parse` for structured
  output, writes `extracted_signals`.
- **`dedup.py`** — `dedup_agent`: embeds each signal (`text-embedding-3-small`),
  clusters near-duplicates via union-find at a tuned similarity threshold,
  writes `signal_clusters`.
- **`brief.py`** — `brief_writer`: Claude Sonnet synthesizes clusters into a
  markdown brief, diffing against the previous week's brief for the same
  competitor, writes `briefs`.
- **`graph.py`** — wires the above into the LangGraph `StateGraph` and
  compiles it; every LLM-calling function accepts `api_key: str | None`,
  passed straight to the SDK client (`None` -> SDK falls back to the
  `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` env var).

### `routers/`

- **`competitors.py`** — CRUD for competitors (user-scoped via `user_id`),
  `POST /competitors/{id}/run` (runs the graph synchronously, merging in the
  user's decrypted API keys), `GET /competitors/{id}/briefs`.
- **`internal.py`** — `/internal/run-all` (runs every competitor for every
  user, per-competitor error isolation) and `/internal/send-digest`, both
  gated by a shared-secret header (`X-Internal-Secret`) instead of user JWTs
  — called by the GitHub Actions cron, not by the frontend.
- **`settings.py`** — `GET`/`PUT /me/api-keys` for BYOK key management.

## Frontend (`frontend/src/app`)

Next.js 14 App Router. Server components fetch data directly from the
backend on the server (via `lib/api.js`'s `apiFetch`, which forwards the
NextAuth session as a `Bearer` token); client components (`RunButton`,
forms) handle interactivity.

- **`login/`, `signup/`** — Auth.js credential-based auth, MongoDB adapter,
  bcrypt password hashing, JWT session strategy (`AUTH_SECRET` shared with
  the backend so the same token verifies on both sides).
- **`page.jsx`** (dashboard) — lists the user's competitors.
- **`competitors/new`** — add-competitor form (name + per-source config).
- **`competitors/[id]/page.jsx`** — competitor detail: configured sources,
  "Run now" button, and briefs rendered with `react-markdown` +
  `@tailwindcss/typography`.
- **`settings/`** — BYOK page: save/clear OpenAI and Anthropic keys (never
  displays the actual key back, only "set"/"not set" status).

## Data model (MongoDB collections)

| Collection | Written by | Purpose |
|---|---|---|
| `users` | Auth.js adapter / settings router | account + encrypted API keys |
| `competitors` | `competitors.py` | per-user tracked competitors + source config |
| `raw_signals` | `save_to_mongo` | unprocessed output from the 6 source agents |
| `extracted_signals` | `extract_agent` | structured `(title, summary, category, date)` |
| `signal_clusters` | `dedup_agent` | deduplicated groups of extracted signals |
| `briefs` | `brief_writer` | final markdown digest per competitor per run |

## Deployment topology

- **Backend** -> Render (Docker, `backend/Dockerfile`, production command
  without `--reload`). Env vars set in the Render dashboard from
  `.env.example`.
- **Frontend** -> Vercel (native Next.js build, no Dockerfile needed —
  Vercel's build pipeline runs `next build`/`next start` directly). Env vars
  set in the Vercel dashboard; `BACKEND_URL` points at the Render backend's
  public URL.
- **Scheduling** -> GitHub Actions cron calls the deployed backend's
  `/internal/run-all` and `/internal/send-digest`, with a retry loop to
  handle Render free-tier cold starts.
- **Local dev** -> `docker-compose.yml` runs both services together with
  service-name networking (`BACKEND_URL=http://backend:8000`).
