# AI Pair Programming Chat Log

This log captures key architectural and implementation interactions, prompts, iterations, and decision points during the development of the Mini Hiring Pipeline.

---

## Session 1: Project Setup & Containerization

### User Prompt
> Project setup and containerization with Docker Compose, FastAPI, and PostgreSQL.

### Assistant Action
- Created project skeleton (`app/`, `db/`, `tests/`, `docs/`, `chat_logs/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`).
- Configured PostgreSQL 16 service with healthchecks and FastAPI service with hot-reloading.

---

## Session 2: Schema Design & Database Immutability

### User Prompt
> Step 3: Database schema with immutability. `db/init.sql` with `candidates`, `stage_events`, append-only triggers, and `candidate_current` derived view.

### Assistant Action
- Created [`db/init.sql`](file:///d:/interview/hiring-pipeline/db/init.sql) with PL/pgSQL function `forbid_change()` raising exceptions on `UPDATE`, `DELETE`, or `TRUNCATE`.
- Created dynamic view `candidate_current` using `JOIN LATERAL` on the latest event to guarantee state consistency with audit history.

---

## Session 3: State Machine & Pipeline Validation

### User Prompt
> Step 5: State machine (pure logic, no DB). `app/pipeline.py` with `validate_move` and comprehensive tests.

### Assistant Action
- Implemented `STAGES`, `NEXT`, `FINAL` and `validate_move(current, target)`.
- Wrote unit tests in [`tests/test_pipeline.py`](file:///d:/interview/hiring-pipeline/tests/test_pipeline.py) testing valid linear progressions, stage skipping rejection, backward movement prevention, and terminal state locking (`Hired`/`Rejected`).

---

## Session 4: REST API Endpoints & Immutability Integration Tests

### User Prompt
> Step 6 & 7: REST API and immutability tests. `POST /candidates`, `GET /candidates`, `GET /candidates/{cid}`, `POST /candidates/{cid}/move`, and DB trigger integration tests.

### Assistant Action
- Implemented FastAPI routing in [`app/main.py`](file:///d:/interview/hiring-pipeline/app/main.py) with row-locking (`SELECT 1 FROM candidates WHERE id=%s FOR UPDATE`) to eliminate race conditions during concurrent moves.
- Implemented `tests/test_api.py` validating API responses and executing raw SQL `UPDATE`, `DELETE`, and `TRUNCATE` assertions against the trigger.

---

## Session 5: Natural Language Search, Fuzzy Matching & Damerau-Levenshtein

### User Prompt
> Step 8 & 9: Search parser, Damerau-Levenshtein distance, and candidate ranking.

### Discussion & Technical Deep-Dive
- Implemented regex tokenization for stage inclusions, exclusions, historical events (`reached <stage> but not hired`), and temporal ranges (`since monday`, `stuck in screening`).
- Implemented Damerau-Levenshtein algorithm where single adjacent transpositions (e.g. `sharam` vs `sharma`) cost 1 edit distance rather than standard Levenshtein's 2 edits.
- Added comprehensive unit tests in [`tests/test_search_parser.py`](file:///d:/interview/hiring-pipeline/tests/test_search_parser.py).

---

## Session 6: Search Endpoint & Kanban Board Web UI

### User Prompt
> Step 10 & 11: Implement `/search` endpoint combining SQL parameter filtering with Python fuzzy scoring, plus a minimal responsive UI.

### Assistant Action
- Built `GET /search?q=...` returning structured interpretations (`describe(f)`), matching candidate cards, and scores.
- Implemented full Kanban board in [`app/static/index.html`](file:///d:/interview/hiring-pipeline/app/static/index.html) with:
  - Real-time search highlighting and interpretation banner
  - Interactive "Next" and "Reject" transitions with optional audit notes
  - Candidate history drawer displaying duration in stage and full event log
  - Candidate creation modal

---

## Session 7: Seed Data & Testing

### User Prompt
> Step 12: Add `scripts/seed.py` with 10 sample candidates, historical dates, and duration milestones.

### Assistant Action
- Created and executed [`scripts/seed.py`](file:///d:/interview/hiring-pipeline/scripts/seed.py) providing candidates with varied timelines to demonstrate `"stuck for > 7 days"`, `"moved to interview since monday"`, and fuzzy match queries.
