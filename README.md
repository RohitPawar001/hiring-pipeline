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

*(Add architectural details, decisions, trade-offs, and future improvements here)*
