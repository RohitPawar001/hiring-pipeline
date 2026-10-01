# Mini Hiring Pipeline

A web application designed for recruiters to manage candidate stages (Applied → Screening → Interview → Offer → Hired / Rejected), track candidate stage duration & immutable audit history, and perform intelligent candidate searches.

---

## 🐳 Quick Start with Docker Compose (Recommended)

The easiest way to run the application along with PostgreSQL is using Docker Compose:

### 1. Build and Start Services

```bash
docker compose up --build
```

This will:
- Spin up a **PostgreSQL 16** database container initialized with [`db/init.sql`](file:///d:/interview/hiring-pipeline/db/init.sql).
- Build the FastAPI application image using [`Dockerfile`](file:///d:/interview/hiring-pipeline/Dockerfile).
- Run the server at `http://localhost:8000`.

### 2. Access the Application

- **Web App / UI:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Stop Services

```bash
docker compose down
```

---

## 💻 Local Development Setup

If you prefer running the application locally:

### 1. Install `uv`

* **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
* **macOS / Linux:**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
* **pip (Alternative):**
  ```bash
  pip install uv
  ```

---

### 2. Create Virtual Environment

```bash
uv venv
```

---

### 3. Activate Virtual Environment

* **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\activate
  ```
* **Windows (Command Prompt `cmd`):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
* **macOS / Linux (Bash / Zsh):**
  ```bash
  source .venv/bin/activate
  ```

---

### 4. Install Dependencies

```bash
uv pip install -r requirements.txt
```

---

### 5. Run Locally

Ensure PostgreSQL is running locally, then start the Uvicorn server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🏗 Architecture & Design Decisions

### 📊 1. Event Sourcing & Database Immutability
The pipeline uses an **append-only event model** for tracking candidate stage transitions rather than mutating status in-place:
- **`candidates` table:** Stores candidate identity (`id`, `name`, `email`, `created_at`).
- **`stage_events` table:** Append-only log capturing every transition (`candidate_id`, `from_stage`, `to_stage`, `occurred_at`, `note`).
- **Database-Level Immutability:** PostgreSQL triggers (`no_update_delete` and `no_truncate`) enforce strict append-only constraints at the DB level via `forbid_change()`, preventing any `UPDATE`, `DELETE`, or `TRUNCATE` operations on `stage_events`.
- **`candidate_current` Derived View:** Current stage is derived dynamically using a `LATERAL` join on the most recent event (`ORDER BY id DESC LIMIT 1`), guaranteeing that current state can never drift or disagree with history.

#### Verifying Immutability in PostgreSQL

```bash
docker compose exec -it db psql -U postgres -d hiring_db -c "UPDATE stage_events SET note='test';"
# Output: ERROR: stage_events is append-only
```

### 🔒 2. Concurrency Control
When moving a candidate (`POST /candidates/{cid}/move`), the backend locks the candidate row using `SELECT 1 FROM candidates WHERE id=%s FOR UPDATE`. This row-level lock serializes concurrent move attempts, preventing race conditions where two simultaneous moves might both pass validation.

### 🔍 3. Rule-Based Natural Language Parser vs. LLM
Instead of introducing an expensive, slow, non-deterministic LLM or heavy NLP library for single-box search, we implemented a custom rule-based query parser:
- **Fast & Deterministic:** Sub-millisecond parsing using regular expressions and domain vocabulary.
- **Actionable Feedback:** Explains *why* impossible or contradictory queries fail (e.g. requesting `"hired and rejected"` returns `HTTP 422: A candidate can only be in one stage at a time...`).
- **Query Interpretation:** Provides recruiters with immediate feedback on how their search was parsed (`Interpreted as: name ≈ "sharma", stage = Screening`).

### 🔤 4. Damerau-Levenshtein Fuzzy Matching & Ranking
Standard Levenshtein distance treats adjacent character transposition (e.g., `sharam` vs `sharma`) as **2 edits** (one deletion + one insertion). We implemented custom Damerau-Levenshtein distance where adjacent transpositions count as **1 edit**. Scoring prioritizes exact matches (100) > prefix/token matches (80) > substring matches (60) > fuzzy DL transposition matches (>30).

### ⏱ 5. Timezones & Duration Semantics
- **Timezone Awareness:** The app uses `APP_TZ` (`Asia/Kolkata` by default, configurable via Docker environment) to ensure `since Monday` and `yesterday` resolve accurately to midnight of the recruiter's local day.
- **"Stuck" Semantics:** Duration searches like `"stuck in Screening"` or `"in Screening > 7 days"` explicitly apply only to active candidates in the pipeline, automatically excluding finished terminal outcomes (`Hired` and `Rejected`).

---

## 💡 Where I Disagreed with the AI

### Example 1: Test Teardown via `TRUNCATE`
* **AI Proposal:** During test setup design, the AI suggested cleaning up test data between pytest runs using `TRUNCATE candidates CASCADE`.
* **Why I Disagreed:** Our database triggers strictly attach `BEFORE TRUNCATE` on `stage_events` which executes `forbid_change()`. Running a cascading truncate on `candidates` automatically triggers PostgreSQL to truncate child tables, causing the test suite to fail on its own database integrity trigger.
* **What I Did Instead:** Disagreed with truncating tables during tests. Instead, implemented isolated test fixtures using unique UUID-suffixed names (`unique_name()`) per test run. This guarantees complete test independence while keeping the database immutability triggers active and verifiable.

### Example 2: Typo Matching via Standard Levenshtein vs Damerau-Levenshtein
* **AI Proposal:** An earlier draft suggested using Python's standard `levenshtein()` distance algorithm for name scoring.
* **Why I Disagreed:** Recruiters frequently make single-keystroke transpositions (typing `sharam` instead of `sharma`). Standard Levenshtein calculates distance as 2 (cost of substitution/delete-insert), dropping the score below the match threshold.
* **What I Did Instead:** Implemented a full Damerau-Levenshtein algorithm with transposition matrix logic (`d[i][j] = min(d[i][j], d[i-2][j-2] + 1)`), accurately evaluating `sharam` &rarr; `sharma` with an edit distance of **1**.

---

## ⚠️ Limitations & Future Improvements

### Current Limitations
1. **Single-Job Scope:** Designed for a single requisition/pipeline.
2. **In-Memory Scorer Scale:** SQL filters stage and date parameters, but fuzzy name scoring is evaluated in Python. This is fast for hundreds or low thousands of candidates, but would not scale to hundreds of thousands without database-level indexing.
3. **No Auth/Actor Tracking:** History records timestamps, stages, and notes, but does not capture recruiter identity.

### What I'd Do with More Time
1. **Authentication & Multi-Tenant Recruiter Roles:** Add JWT/session auth and an `actor_id` field to `stage_events` to record *who* moved the candidate.
2. **Database-Level Trigram Search (`pg_trgm`):** For larger datasets (>100k candidates), add PostgreSQL `pg_trgm` with a GiST/GIN index on `candidates.name` to perform typo-tolerant fuzzy matching directly in SQL.
3. **Pagination & Infinite Scroll:** Implement cursor-based pagination for `GET /candidates` and `/search` to support enterprise pipelines.
4. **Rich Date Expressions & OR Logic:** Expand the search parser to support boolean disjunctions (`"sharma or patel"`, `"in screening or interview"`) and relative offsets (`"last week"`, `"3 months ago"`).
5. **Real-time Updates (WebSockets / SSE):** Push live stage changes to recruiter dashboards when another team member moves a candidate.

---


---

## 📡 REST API Endpoints

The API provides endpoints to manage candidate progression through the hiring pipeline:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/candidates` | Add a candidate (starts at `Applied` stage) |
| `GET` | `/candidates` | Retrieve candidate board grouped by stages |
| `GET` | `/candidates/{cid}` | Get candidate details, days in stage, & full transition history |
| `POST` | `/candidates/{cid}/move` | Transition candidate to the next valid stage (row-locked) |
| `GET` | `/search?q=...` | Natural language candidate search with query interpretation & fuzzy scoring |

> **Note on Duration Searches:** Searches with duration constraints such as `"stuck in Screening"` or `"in Screening > 7 days"` automatically filter for active candidates and exclude terminal outcomes (`Hired` / `Rejected`).

---

## 🌱 Seeding & Demo Data

A seed script is provided to populate the pipeline with sample candidates spanning various stages, explicit historical timestamps, notes, and duration metrics (useful for testing `"stuck for a week"`, `"since Monday"`, and fuzzy searches):

### Run Seed Script via Docker Compose

```bash
docker compose exec app python scripts/seed.py
```

### Run Seed Script Locally

```bash
python scripts/seed.py
```

---


## 🧪 Testing

The test suite covers pure logic state machine validation, full API integration, and PostgreSQL immutability guarantees.

### Test Suites Included

- **`tests/test_pipeline.py` (State Machine Logic):**
  - Sequential progression validation (`Applied` → `Screening` → `Interview` → `Offer` → `Hired`)
  - Stage-skipping and backward-movement prevention
  - Non-final stage rejection support
  - Terminal state validation (`Hired` / `Rejected` cannot transition)

- **`tests/test_api.py` (FastAPI & Immutability Integration):**
  - Candidate creation and initial state assignment (`Applied`)
  - HTTP 422 error handling for invalid/skipped moves and terminal stage transitions
  - Complete history log integrity & event sequencing
  - Direct database trigger assertions verifying `UPDATE`, `DELETE`, and `TRUNCATE` operations raise exceptions on `stage_events`

- **`tests/test_search_parser.py` (Natural Language Search Parser):**
  - Stopword filtering and candidate name extraction
  - Single/multiple stage inclusion and exclusion handling
  - Historical transition tracking (`reached <stage> [but not hired]`)
  - Temporal queries (`moved to <stage> since <day|date>`, duration thresholds `stuck`, `more than X days/weeks`)
  - Error catching for impossible stage combinations, invalid stage names, and future dates


### Running Tests with Docker Compose

```bash
docker compose exec app pytest tests/ -v
```

### Running Tests Locally

```bash
pytest tests/ -v
```





