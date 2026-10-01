# Mini Hiring Pipeline

A web application designed for recruiters to manage candidate stages (Applied → Screening → Interview → Offer → Hired / Rejected), track candidate stage duration & immutable audit history, and perform intelligent candidate searches.

![Mini Hiring Pipeline Board](docs/assets/pipeline_board.png)

<p align="center">
  <img src="docs/assets/add_candidate_modal.png" width="48%" alt="Add Candidate Modal" />
  <img src="docs/assets/how_to_use_modal.png" width="48%" alt="How to Use Guide Modal" />
</p>

---

## 🐳 Quick Start with Docker Compose (Recommended)

The easiest and cleanest way to run the entire application along with PostgreSQL is using Docker Compose.

### 📋 Prerequisites

Before running the project with Docker:
1. **Docker Desktop / Docker Engine:** Ensure Docker is installed and actively running.
   - [Install Docker Desktop for Windows / Mac / Linux](https://www.docker.com/products/docker-desktop/)
2. **Verify Docker CLI Installation:**
   ```bash
   docker --version
   docker compose version
   ```
3. **Ports Availability:** Ensure host port `8000` (Web App/API) and port `5432` (PostgreSQL) are free.

---

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
- **Pipeline Config Endpoint:** [http://localhost:8000/config](http://localhost:8000/config)

### 3. Stop Services

```bash
docker compose down
```

---

## 💻 Local Development Setup (Without Docker App)

If you wish to run the FastAPI backend locally via `uvicorn` on your host machine while using the Dockerized PostgreSQL database:

### 1. Start Only the PostgreSQL Database Container

```bash
docker compose up -d db
```

### 2. Set Up Virtual Environment & Dependencies

```bash
# Using uv
uv venv
uv pip install -r requirements.txt

# Or using standard venv
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Set the Database Connection String

If your local host has a native PostgreSQL service installed on port `5432`, ensure `DATABASE_URL` points to the correct port to avoid `password authentication failed` conflicts.

**PowerShell (Windows):**
```powershell
$env:DATABASE_URL = "postgresql://app:app@localhost:5432/hiring"

# Direct runner:
uv run main.py
# Or via uvicorn directly:
uv run uvicorn app.main:app --reload --port 8000
```

**Bash / macOS / Linux:**
```bash
export DATABASE_URL="postgresql://app:app@localhost:5432/hiring"

# Direct runner:
python main.py
# Or via uvicorn directly:
uvicorn app.main:app --reload --port 8000
```

### 4. Access the Application

- **Web App / UI:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Pipeline Config Endpoint:** [http://localhost:8000/config](http://localhost:8000/config)

---

## 🖥️ Using the Web UI

Once the application is running, open **[http://localhost:8000](http://localhost:8000)** in your browser to interact with the Kanban pipeline and smart search.

### 1. Kanban Pipeline Board
- **Columns (In Order):** `Applied` → `Screening` → `Interview` → `Offer` → `Hired`, plus `Rejected`.
- **Card Information:** Each card displays candidate name, ID, email, stage entry date, and active days spent in that stage.
- **Stage Progression:**
  - Click **Next → [Stage]** to advance the candidate strictly to the next valid stage.
  - Click **Reject** to disqualify a candidate at any non-final stage.
  - An optional **Audit Note** modal allows adding context (e.g. *"Passed system design round"*), which is permanently appended to the candidate's history log.
- **Add Candidate:** Click **+ Add Candidate** in the top bar to create a candidate directly in the initial `Applied` stage.

### 2. Candidate Detail & Audit Drawer
- Click anywhere on a candidate's card to open the **Candidate Detail Drawer**.
- Displays total duration in the current stage (e.g., `4.2 days in Interview`).
- Shows the complete **Append-Only Timeline** detailing every historical transition timestamp, previous stage, new stage, and audit notes.

### 3. Natural Language Search Box
Type intuitive queries in the top search bar and press <kbd>Enter</kbd> (or click **Search**):

| Example Query | What It Does |
|---|---|
| `sharam` | **Fuzzy Typo-Tolerant Match** finds *"Rohit Sharma"* via Damerau-Levenshtein transposition. |
| `in Screening` | Filters candidates currently in the **Screening** stage. |
| `stuck in Interview` | Finds active candidates in **Interview** for **> 7 days**. |
| `in Screening more than 3 days` | Filters active candidates in **Screening** for **> 3 days**. |
| `moved to Interview since Monday` | Filters candidates who transitioned to **Interview** on or after this past Monday. |
| `reached Offer but not hired` | Historical filter for candidates who reached the **Offer** stage but are not currently Hired. |
| `everyone except rejected` | Filters out candidates in the **Rejected** column. |
| `sharma in Screening` | Combines name search and stage filter with weighted score ranking. |

- **Query Interpretation:** The UI shows how your query was parsed (e.g., `🔍 Interpreted as: name ≈ "sharma", stage = Screening`).
- **Matching Highlights:** Matching candidate cards are highlighted in blue on the board.
- **Helpful Validation Errors:** Contradictory searches (e.g. `hired and rejected` or `stage invalid`) display clear explanations in red rather than failing silently.


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

## 🏗 Architecture & System Flow Diagrams

### 1. High-Level System Architecture

```mermaid
graph TD
    User["👤 Recruiter / Web Browser"]
    
    subgraph Frontend ["🎨 Frontend (Single-Page App)"]
        UI["Vanilla JS + CSS (index.html)"]
        Board["Kanban Pipeline Board"]
        Search["Natural Language Search Box"]
        Drawer["Audit History Timeline Drawer"]
        Modal["Move & Audit Note Modal"]
    end
    
    subgraph Backend ["⚡ FastAPI Application (/app)"]
        Main["main.py (App & Static Mount)"]
        ConfigRoute["/config (Pipeline Specs)"]
        CandRoute["/candidates (CRUD & Move)"]
        SearchRoute["/search (NL Query & Ranking)"]
        
        SM["Pipeline State Machine (pipeline.py)"]
        NLP["NL Query Parser (search.py)"]
        DL["Damerau-Levenshtein Scorer"]
        DBPool["Connection Manager (db.py)"]
    end
    
    subgraph Database ["🐘 PostgreSQL 16 (Event-Sourced)"]
        CandTable[("candidates Table<br/>(id, name, email, created_at)")]
        EventTable[("stage_events Table<br/>(Append-Only Log)")]
        Triggers["💥 PL/pgSQL Immutability Triggers<br/>(BEFORE UPDATE/DELETE/TRUNCATE)"]
        CurrentView["👁️ candidate_current View<br/>(LATERAL JOIN Latest Event)"]
    end

    User <--> UI
    UI --> Board & Search & Drawer & Modal
    
    Board <--> CandRoute & ConfigRoute
    Search <--> SearchRoute
    Modal --> CandRoute
    Drawer <--> CandRoute

    CandRoute --> SM & DBPool
    SearchRoute --> NLP & DL & DBPool
    
    DBPool --> CandTable & EventTable & CurrentView
    EventTable --- Triggers
    CandTable -.-> CurrentView
    EventTable -.-> CurrentView
```

### 2. Candidate State Machine & Stage Progression

```mermaid
stateDiagram-v2
    [*] --> Applied: POST /candidates (Auto-Created)
    
    Applied --> Screening: Next → Screening
    Screening --> Interview: Next → Interview
    Interview --> Offer: Next → Offer
    Offer --> Hired: Next → Hired (Final Stage 🔒)
    
    Applied --> Rejected: Disqualify (with Audit Note)
    Screening --> Rejected: Disqualify (with Audit Note)
    Interview --> Rejected: Disqualify (with Audit Note)
    Offer --> Rejected: Disqualify (with Audit Note)
    
    Rejected --> [*]: Final Outcome 🔒 (No moves allowed)
    Hired --> [*]: Final Outcome 🔒 (No moves allowed)
```

---

## 🏛️ Design Decisions & Core Pillars

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

## 📡 REST API Endpoints & Swagger Docs

![Interactive Swagger API Docs](docs/assets/api_swagger_docs.png)

The API provides modular endpoints to manage candidate progression through the hiring pipeline:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/config` | Retrieve pipeline stages, allowed transitions, final states, and timezone |
| `POST` | `/candidates` | Add a candidate (starts at `Applied` stage) |
| `GET` | `/candidates` | Retrieve candidate board grouped by stages with active duration |
| `GET` | `/candidates/{cid}` | Get candidate details, days in stage, & full transition history |
| `POST` | `/candidates/{cid}/move` | Transition candidate to the next valid stage (row-locked) |
| `GET` | `/search?q=...` | Natural language candidate search with query interpretation & fuzzy scoring |

> **Note on Duration Searches:** Searches with duration constraints such as `"stuck in Screening"` or `"in Screening > 7 days"` automatically filter for active candidates and exclude terminal outcomes (`Hired` / `Rejected`).

---

---

## 🌱 Database Initialization & Seeding Demo Data

### 1. Manual / Re-Apply Database Schema (Optional)
When using Docker Compose, [`db/init.sql`](file:///d:/interview/hiring-pipeline/db/init.sql) runs automatically on initial container startup via `/docker-entrypoint-initdb.d/init.sql`. To manually apply or re-run the schema:

```bash
docker compose exec -T db psql -U app -d hiring -f /docker-entrypoint-initdb.d/init.sql
```

### 2. Populate Seed & Demo Data
A seed script is provided to populate the pipeline with sample candidates spanning various stages, explicit historical timestamps, notes, and duration metrics (useful for testing `"stuck for a week"`, `"since Monday"`, and fuzzy searches):

```bash
docker compose exec -T app python scripts/seed.py
```

*Or run locally:*
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





