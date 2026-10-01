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

### 📊 Database Schema & Event Sourcing / Immutability

The pipeline uses an **append-only event model** for tracking candidate stage transitions rather than mutating status in-place:

- **`candidates` table:** Stores candidate identity (`id`, `name`, `email`, `created_at`).
- **`stage_events` table:** Append-only log capturing every transition (`candidate_id`, `from_stage`, `to_stage`, `occurred_at`, `note`).
- **Database-Level Immutability:** PostgreSQL triggers (`no_update_delete` and `no_truncate`) enforce strict append-only constraints at the DB level via `forbid_change()`, preventing any `UPDATE`, `DELETE`, or `TRUNCATE` operations on `stage_events`.
- **`candidate_current` View:** Current stage is derived dynamically using a `LATERAL` join on the most recent event, guaranteeing that the current state can never disagree with audit history.

#### Verifying Immutability in PostgreSQL

```bash
docker compose exec -it db psql -U postgres -d hiring_db -c "UPDATE stage_events SET note='test';"
# Output: ERROR: stage_events is append-only
```

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

> **Interactive API Documentation:** Available at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).


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





