# Applytics — Backend Architecture & Implementation Plan

Status: planning only — no application code written yet.
Scope: backend (FastAPI + PostgreSQL + LangGraph). Frontend (Next.js) is out of scope for this document.

## 0. Current State (as found)

The `backend/` scaffold exists but is empty:

```
backend/
├── .env                  # POSTGRES_USER/PASSWORD/DB, DATABASE_URL, OPEN_API_KEY
├── main.py                # empty
├── requirements.txt        # fastapi, uvicorn, sqlmodel, asyncpg, alembic, pydantic-settings, psycopg2-binary
├── agents/                 # empty
├── api/routes/              # empty
├── core/                   # empty
├── db/migrations/            # empty
├── services/scraper/          # empty
└── tests/                  # empty
```

Root `docker-compose.yml` and `README.md` exist but are empty. `frontend/` is a stock `create-next-app` scaffold, untouched.

Notes on what's missing from `requirements.txt` for the roadmap below: `langgraph`, `langchain`, an LLM provider SDK, `httpx`, an HTML/PDF parser (`beautifulsoup4`, `pypdf`/`python-docx`), auth libs (`python-jose`, `passlib[bcrypt]`), a background task runner (`apscheduler` or `celery`+`redis`), and a test stack (`pytest`, `pytest-asyncio`). These get added per-phase below rather than all at once.

Also flagging: `.env` has `OPEN_API_KEY` — presumably meant to be `OPENAI_API_KEY` (or whichever provider is chosen — see open questions). Worth confirming before Phase 3.

---

## 1. High-Level Architecture

```
                         ┌─────────────────────────┐
                         │   Next.js Frontend       │
                         └────────────┬─────────────┘
                                      │ REST (JSON)
                         ┌────────────▼─────────────┐
                         │   FastAPI (backend/)      │
                         │  api/routes/*  — HTTP layer│
                         └──┬───────┬───────┬────────┘
                            │       │       │
              ┌─────────────▼┐ ┌────▼────┐ ┌▼─────────────────┐
              │ services/      │ │ agents/  │ │ core/             │
              │ (business logic,│ │ (LangGraph│ │ (config, db,      │
              │  scraper adapters)│ │ AI agents)│ │  security, logging)│
              └─────────────┬┘ └────┬────┘ └───────────────────┘
                            │       │
                     ┌──────▼───────▼──────┐
                     │  PostgreSQL (asyncpg) │
                     │  via SQLModel + Alembic│
                     └───────────────────────┘

              External: Adzuna API, LinkedIn/Indeed/Glassdoor/Jobwright
              (scraping or partner APIs), LLM provider (OpenAI/etc.)
```

Layering conventions:
- `api/routes/*` — thin HTTP handlers only: parse request → call a service/agent → shape response. No business logic here.
- `services/*` — business logic and I/O boundaries: DB CRUD, the scraper adapters, resume/LinkedIn parsing, application tracking logic.
- `agents/*` — LangGraph graphs and LangChain chains for AI evaluation (profile comparison, keyword strength, location impact, market research). Agents call services for data, never the other way around.
- `core/*` — cross-cutting: `config.py` (pydantic-settings), `db.py` (async engine/session), `security.py` (auth/JWT), `logging.py`.
- `db/migrations/*` — Alembic migration scripts, versioned against `SQLModel.metadata`.

Async end-to-end: FastAPI async routes, `asyncpg`-backed SQLModel sessions, and scraping/LLM calls via async HTTP clients (`httpx.AsyncClient`) so scrape runs and multi-agent evaluations don't block the event loop.

---

## 2. Proposed Database Schema

```
business_developer
├── id (PK, uuid)
├── email (unique)
├── hashed_password
├── full_name
├── role                      # enum: bd, admin
├── created_at

client                         # a BD's end-customer whose career they manage
├── id (PK, uuid)
├── bd_id (FK -> business_developer.id)
├── full_name
├── email
├── current_city / current_state / current_country
├── timezone
├── status                     # enum: active, paused, placed, churned
├── created_at

target_role                    # a job title/track this client is being marketed for
├── id (PK, uuid)
├── client_id (FK -> client.id)
├── title                      # e.g. "Senior Backend Engineer"
├── seniority
├── must_have_keywords (JSONB)
├── created_at

profile                        # a resume OR linkedin profile, versioned for A/B testing
├── id (PK, uuid)
├── client_id (FK -> client.id)
├── target_role_id (FK -> target_role.id, nullable)
├── type                       # enum: resume, linkedin
├── variant_label               # e.g. "A", "B", "v2-keyword-heavy"
├── source_url                  # linkedin url, or storage path for resume file
├── raw_text                    # extracted plain text
├── structured_data (JSONB)      # parsed skills/experience/education, LLM-normalized
├── is_active
├── created_at

job_source                     # config per external board
├── id (PK)
├── name                       # adzuna, linkedin, indeed, glassdoor, jobwright
├── auth_config (JSONB)          # api key ref / scrape config, not secrets themselves
├── rate_limit_per_min
├── is_enabled

scrape_run
├── id (PK, uuid)
├── job_source_id (FK)
├── filters (JSONB)              # {remote: "fully", country: "US", ...}
├── status                     # enum: running, success, failed
├── jobs_found_count
├── started_at / finished_at
├── error_message

job
├── id (PK, uuid)
├── job_source_id (FK)
├── external_id                 # dedupe key together with job_source_id
├── title
├── company
├── location_raw
├── remote_type                 # enum: fully_remote, hybrid, onsite
├── country
├── description
├── apply_url
├── posted_at
├── scraped_at
├── raw_payload (JSONB)
├── UNIQUE(job_source_id, external_id)

application                    # a client applying to a job using a specific profile variant
├── id (PK, uuid)
├── client_id (FK)
├── profile_id (FK)             # which variant was used — feeds A/B results
├── job_id (FK)
├── applied_at
├── status                     # enum: applied, screening, interview, offer, rejected
├── status_updated_at
├── notes

comparison_run                  # the A/B evaluation between two (or more) profile variants
├── id (PK, uuid)
├── client_id (FK)
├── target_role_id (FK)
├── profile_ids (JSONB array)     # supports N-way, not just A/B
├── status                     # enum: pending, running, complete, failed
├── result_summary (text)
├── result_detail (JSONB)        # per-profile scores, bottlenecks, strengths/weaknesses
├── winner_profile_id (FK, nullable)
├── created_at / completed_at

keyword_analysis
├── id (PK, uuid)
├── profile_id (FK)
├── target_role_id (FK, nullable)
├── extracted_keywords (JSONB)
├── missing_keywords (JSONB)
├── ats_score
├── recruiter_attention_score
├── created_at

location_analysis
├── id (PK, uuid)
├── client_id (FK)
├── target_role_id (FK, nullable)
├── location_penalty_score       # how much current location likely hurts fully-remote US odds
├── recommendation (text)
├── created_at

agent_run                       # observability/cost log for every LLM call
├── id (PK, uuid)
├── agent_type                  # keyword, location, comparison, market_research
├── related_entity_type / related_entity_id  # polymorphic pointer (comparison_run, profile, ...)
├── model_name
├── prompt_tokens / completion_tokens
├── latency_ms
├── status                     # enum: success, error
├── created_at
```

Design notes:
- `profile.variant_label` + `client_id` + `target_role_id` is what makes the A/B testing engine queryable: "all variants for client X targeting role Y."
- `comparison_run.profile_ids` as a JSONB array (not a fixed profile_a/profile_b pair) so the engine isn't hard-capped at exactly two variants if BDs want N-way tests later — cheap to build in now, expensive to retrofit.
- `agent_run` exists from day one because LLM cost/latency tracking is much harder to bolt on retroactively than to design in alongside the first agent.
- All PKs are UUIDs (multi-tenant data, safer to not leak sequential IDs via API).

---

## 3. Phased Roadmap

### Phase 0 — Foundations & Infra
- `core/config.py`: `Settings(BaseSettings)` reading `.env` (DB URL, LLM key, JWT secret).
- `core/db.py`: async engine (`create_async_engine` w/ `asyncpg` driver) + `AsyncSession` factory + FastAPI dependency.
- `main.py`: FastAPI app factory, CORS, health check (`GET /health`), router registration.
- Alembic init wired to `SQLModel.metadata`, async-compatible `env.py`.
- `docker-compose.yml`: `postgres` service (+ volume) and `backend` service; confirm it matches the existing `.env` credentials.
- Update `requirements.txt` for this phase: nothing new yet, base deps already present.

### Phase 1 — Core Domain: Auth, BD, Client, Profile
- SQLModel models: `BusinessDeveloper`, `Client`, `TargetRole`, `Profile`. First Alembic migration.
- `core/security.py`: password hashing (`passlib[bcrypt]`) + JWT issuing/verification (`python-jose`).
- CRUD endpoints: `/auth/login`, `/bds/me`, `/clients`, `/clients/{id}/target-roles`, `/profiles` (create/list/get, scoped to the authenticated BD's clients).
- Profile ingestion service: PDF/DOCX → `raw_text` (`pypdf`, `python-docx`); LinkedIn URL → stored for later scraping/parsing.
- Deps added: `python-jose[cryptography]`, `passlib[bcrypt]`, `pypdf`, `python-docx`.

### Phase 2 — Job Scraper Service
- `services/scraper/base.py`: abstract `JobScraper` interface (`fetch(filters) -> list[JobPayload]`).
- Adapters: `AdzunaScraper` (official API, easiest/safest), then `IndeedScraper`, `GlassdoorScraper`, `LinkedInScraper`, `JobwrightScraper` — implementation approach (official API vs. licensed data vs. scraping) depends on Open Question #1 below.
- `job_source`, `scrape_run`, `job` models + migration; upsert-on-`(job_source_id, external_id)`.
- Filter engine enforcing BD-specified constraints (100% remote, US-only, role keywords).
- Scheduling: `APScheduler` for periodic runs to start; revisit Celery+Redis only if scrape volume/retry needs outgrow it.
- Endpoints: `POST /scrape/runs`, `GET /jobs` (filtered/paginated), `GET /jobs/{id}`.
- Deps added: `httpx`, `apscheduler`, and a scrape/parse lib once the sourcing approach is confirmed (`beautifulsoup4` and/or `playwright`).

### Phase 3 — AI Evaluation Agents (LangGraph)
- Confirm LLM provider + fix the `.env` key name (Open Question #4).
- `agents/keyword_agent.py`: scores resume/LinkedIn keyword strength against target-role requirements and (once Phase 2 lands) live job description corpus; writes `keyword_analysis`.
- `agents/location_agent.py`: assesses whether `client.current_*` location plausibly hurts fully-remote US applications; writes `location_analysis`.
- `agents/comparison_agent.py`: LangGraph graph — nodes: load profiles → parse/normalize → score each independently → diff → synthesize bottlenecks/strengths → pick a winner (or "insufficient data"); writes `comparison_run`.
- `agents/market_research_agent.py`: aggregates scraped `job` rows for a target role to surface market-level signals (demand, common required keywords, typical seniority).
- All agents log every LLM call to `agent_run` (tokens, latency, cost) and use Pydantic-typed structured output, not free-text parsing.
- Endpoints: `POST /analysis/compare`, `POST /analysis/keywords`, `POST /analysis/location`, `GET /analysis/comparisons/{id}`.
- Deps added: `langgraph`, `langchain`, provider SDK (e.g. `langchain-openai`).

### Phase 4 — Application Tracking & Feedback Loop
- `application` model + migration; endpoints to log an application (client + profile variant + job) and update its status as it progresses.
- Dashboard aggregation endpoints: per-profile-variant performance (application → interview conversion rate) — this is the *ground-truth* signal that should eventually outweigh the AI's pre-application prediction in `comparison_run`.
- Background job to periodically re-run `comparison_agent` once enough application outcomes exist for a client/role, so recommendations improve over time instead of being frozen at profile-creation time.

### Phase 5 — Testing, Observability, Hardening
- `pytest` + `pytest-asyncio`; a dockerized/test Postgres for integration tests; fixtures/factories per model.
- Structured logging + request-id middleware; centralized exception handlers → consistent error JSON shape.
- Rate limiting on scraper-triggering and analysis endpoints (LLM/scrape calls are the expensive path).
- `Dockerfile` for the backend service, finalize `docker-compose.yml` for local dev (postgres + backend, + redis only if Celery was adopted in Phase 2).
- Basic CI checklist: lint (`ruff`), type-check, `pytest`.

---

## 4. Open Questions Before Writing Code

1. **Scraper legality/access per source.** LinkedIn, Indeed, and Glassdoor ToS generally prohibit direct scraping and actively block it (IP bans, legal risk). Adzuna has an official public API. Do we have (or plan to get) licensed/partner API access for the others, or should Phase 2 start with Adzuna + official APIs only and treat LinkedIn/Indeed/Glassdoor/Jobwright as manual-import or third-party-aggregator (e.g. via a paid job-board API reseller) until access is sorted out?
2. **Tenancy/RBAC model.** Does every BD only ever see their own clients, or is there an agency-admin role with visibility across all BDs' clients/data? This changes the auth design and every query's scoping logic in Phase 1.
3. **What "performance" means for the A/B engine.** Should `comparison_run` be scored purely from resume/profile content via the LLM (works with zero applications, but is a prediction), from actual application outcomes (interview/response rate — requires application volume to be statistically meaningful), or a blend? This affects whether Phase 3 can ship usefully before Phase 4.
4. **LLM provider, budget, and expected volume.** `.env` has `OPEN_API_KEY` (likely a typo for `OPENAI_API_KEY`, or a different provider entirely) — confirm provider/model, per-BD or per-client usage budget, and expected daily volume (profiles analyzed/day, scrape frequency) so Phase 2/3 rate limiting and async task sizing aren't guessed at.
5. **Data retention & consent.** Client resumes, LinkedIn URLs, and location data are PII. Any retention limits, deletion requirements, or explicit client consent needed before we scrape job boards and run LLM analysis against a client's profile — anything GDPR/CCPA-relevant to design for from the start rather than retrofit?
