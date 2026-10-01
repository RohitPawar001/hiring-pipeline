# What they want you to build

Think of it as a **mini ATS (Applicant Tracking System)** for one recruiter and one job. It has two parts: a **pipeline board** and a **smart search box**.

## Part 1: Managing the pipeline

**The stages (in order):**
Applied → Screening → Interview → Offer → Hired
A candidate can also be **Rejected** at any point *before* being hired.

**What the app must do:**

1. **Add candidates** and show everyone grouped by stage (like a Kanban/Trello board with columns).
2. **Move one stage at a time.** Rules to enforce:
   - No skipping (Applied → Interview is not allowed).
   - Final outcomes are locked: once **Hired** or **Rejected**, you can't move them again.
3. **Candidate detail page** showing the full history and **how long they've been in the current stage** (e.g., "5 days in Screening").
4. **Immutable audit trail.** Every move is recorded (who, from which stage, to which stage, when), and history entries can **never be edited or deleted**. This is a design/backend rule: append-only, with no update/delete endpoints, and ideally enforced at the database level too (e.g., a trigger that blocks UPDATE/DELETE).

## Part 2: The single search box

One input field that understands different kinds of queries:

| She types | What it means |
|---|---|
| `sharam` | **Fuzzy name match** finds "Priya Sharma" despite the typo |
| `in Interview` | Filter by **current stage** |
| `stuck in Screening for more than a week` | Stage + **time in stage > 7 days** |
| `moved to Interview since Monday` | Filter by **a transition event + date** (from the history) |
| `reached Offer but not hired` | Look at **history**: ever been in Offer, but current stage isn't Hired |
| `everyone except rejected` | **Negation / exclusion** |

**Extra requirements:**
- **Combine** them (e.g., "sharma in Screening more than 7 days").
- **Rank results** so the best matches come first (e.g., exact name match > fuzzy match).
- **Helpful errors:** if the query is nonsense or contradictory (e.g., "hired and rejected", "stage Foo"), show a clear message explaining *why*, not just an empty list.

This is basically building a **small query parser** (tokenize → interpret → filter → score).

## Deliverables

1. **GitHub repo** with a README covering: how to run it, decisions you made and why, and what you'd do with more time.
2. **A PDF** containing the GitHub link and a summary of your architecture.
3. **Your AI chat logs** committed to the repo.
4. **One moment where you disagreed with the AI**, so document it (e.g., the AI suggested a heavy NLP/LLM approach for search, and you chose a simple rule-based parser because it's deterministic and testable).

## What they're really evaluating

- **Correct state machine** (strict transitions, locked final states)
- **Data integrity** (append-only history)
- **Thoughtful search design** (parsing, fuzzy matching, ranking, error messages)
- **Edge cases** (empty input, contradictory filters, timezones for "since Monday", "a week")
- **Communication & judgment** (README, trade-offs, honest AI usage)

## Suggested simple approach

- **Stack:** React + Node/Express (or Python FastAPI) + SQLite.
- **Tables:** `candidates` and `stage_events` (append-only history; current stage derived from the latest event).
- **Search:** rule-based parser with regex/keywords + Levenshtein or trigram fuzzy match for names + simple scoring.
- **Tests:** a handful for transitions and for each example query above.

If you'd like, I can help you pick a stack, design the database schema, or sketch the search parser next.


Yes, PostgreSQL works, and for some parts of this assignment it is actually a better fit than SQLite. The trade-off is that it makes "how to run" longer.

## What PostgreSQL gives you

- **Append-only enforcement is stronger.** Besides triggers, you can `REVOKE UPDATE, DELETE ON stage_events` from the app's database role, so even a bug in your code cannot alter history.
- **Built-in fuzzy search.** The `pg_trgm` extension gives you trigram similarity, so `sharam` vs `Priya Sharma` can be handled in SQL with `similarity()` and a GIN index. Note that trigram similarity is weaker on transpositions than Damerau-Levenshtein, so test it. The `fuzzystrmatch` extension adds `levenshtein()` too.
- **Real timestamps.** `timestamptz` and `AT TIME ZONE` make "since Monday" and "more than a week" cleaner than ISO strings in SQLite.
- **Better concurrency.** Two moves on the same candidate at once can be guarded with `SELECT ... FOR UPDATE`.

## The cost

- The interviewer must have Postgres running to try your app. Fix this with **Docker Compose**: one `docker-compose.yml` with Postgres plus your app, and run instructions become `docker compose up`.
- Tests need a database too. Use a separate test database or a throwaway container.
- For a "mini" app, some reviewers may see it as overkill. Justify it in the README rather than just using it.

## Schema changes (small)

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE candidates (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stage_events (
  id           BIGSERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id),
  from_stage   TEXT,
  to_stage     TEXT NOT NULL CHECK (to_stage IN
               ('Applied','Screening','Interview','Offer','Hired','Rejected')),
  occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  note         TEXT
);

CREATE FUNCTION forbid_change() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'stage_events is append-only'; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_update_delete
  BEFORE UPDATE OR DELETE ON stage_events
  FOR EACH ROW EXECUTE FUNCTION forbid_change();

-- Also block TRUNCATE
CREATE TRIGGER no_truncate
  BEFORE TRUNCATE ON stage_events
  EXECUTE FUNCTION forbid_change();
```

The state machine, parser, and API code stay almost the same. In Python, use `psycopg` (v3) or SQLAlchemy.

## Which should you pick?

- **SQLite:** simplest to run, fewest things that can go wrong in a demo. Good if the time limit is tight.
- **PostgreSQL + Docker Compose:** shows stronger engineering judgment on integrity and search, and `pg_trgm` is a nice talking point. Good if you are comfortable with Docker.

If you go with Postgres, keep the fuzzy matching logic behind one function so you can compare `pg_trgm` against Python-side Damerau-Levenshtein and explain your choice in the README. That also makes a natural spot for your "I disagreed with the AI" example.

Want me to generate the full repo with FastAPI, PostgreSQL, and Docker Compose?


# Step-by-step implementation (Python + FastAPI + PostgreSQL + Docker)

Do these in order. Each step ends with something you can run or test before moving on.

---

## Step 1: Project skeleton

```
hiring-pipeline/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   ├── pipeline.py
│   ├── search.py
│   └── static/index.html
├── db/init.sql
├── tests/
├── chat_logs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

`requirements.txt`
```
fastapi
uvicorn[standard]
psycopg[binary]
pytest
httpx
tzdata
```

`git init` now and commit after each step. A clean commit history is part of what they judge.

---

## Step 2: Docker Compose (so "how to run" is one command)

`docker-compose.yml`
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: hiring
    volumes:
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d hiring"]
      interval: 3s
      retries: 10
  app:
    build: .
    environment:
      DATABASE_URL: postgresql://app:app@db:5432/hiring
      APP_TZ: Asia/Kolkata
    depends_on:
      db: { condition: service_healthy }
    ports: ["8000:8000"]
```

`Dockerfile`
```dockerfile
FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Step 3: Database schema with immutability

`db/init.sql`
```sql
CREATE TABLE candidates (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL CHECK (length(trim(name)) > 0),
  email      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stage_events (
  id           BIGSERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES candidates(id),
  from_stage   TEXT,
  to_stage     TEXT NOT NULL CHECK (to_stage IN
               ('Applied','Screening','Interview','Offer','Hired','Rejected')),
  occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  note         TEXT
);
CREATE INDEX ON stage_events (candidate_id, id DESC);

CREATE FUNCTION forbid_change() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'stage_events is append-only'; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_update_delete BEFORE UPDATE OR DELETE ON stage_events
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
CREATE TRIGGER no_truncate BEFORE TRUNCATE ON stage_events
  EXECUTE FUNCTION forbid_change();

-- Current stage is DERIVED, never stored, so it can't disagree with history
CREATE VIEW candidate_current AS
SELECT c.id, c.name, c.email, e.to_stage AS stage, e.occurred_at AS entered_at
FROM candidates c
JOIN LATERAL (
  SELECT to_stage, occurred_at FROM stage_events
  WHERE candidate_id = c.id ORDER BY id DESC LIMIT 1
) e ON true;
```

**Check:** `docker compose up db`, then in `psql` try `UPDATE stage_events SET note='x';` and confirm it errors.

---

## Step 4: DB connection helper

`app/db.py`
```python
import os, psycopg
from psycopg.rows import dict_row

def get_conn():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
```

---

## Step 5: State machine (pure logic, no DB)

`app/pipeline.py`
```python
STAGES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"]
NEXT = {"Applied": "Screening", "Screening": "Interview",
        "Interview": "Offer", "Offer": "Hired"}
FINAL = {"Hired", "Rejected"}

def validate_move(current: str, target: str) -> str | None:
    """Return an error message, or None if the move is allowed."""
    if target not in STAGES:
        return f"'{target}' is not a valid stage."
    if current in FINAL:
        return f"{current} is a final outcome and cannot change."
    if target == "Rejected":
        return None
    if NEXT[current] != target:
        return f"Cannot move {current} → {target}. Next stage is {NEXT[current]}."
    return None
```

**Test it first (`tests/test_pipeline.py`):** skipping fails, leaving Hired or Rejected fails, rejecting from each non-final stage works, a normal move works, going backward fails.

---

## Step 6: REST API

`app/main.py`
```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .db import get_conn
from .pipeline import validate_move, STAGES

app = FastAPI(title="Mini Hiring Pipeline")

class NewCandidate(BaseModel):
    name: str
    email: str | None = None

class Move(BaseModel):
    to: str
    note: str | None = None

@app.post("/candidates", status_code=201)
def add_candidate(body: NewCandidate):
    if not body.name.strip():
        raise HTTPException(422, "Name is required.")
    with get_conn() as conn:  # one transaction: candidate + first event
        cid = conn.execute(
            "INSERT INTO candidates(name,email) VALUES (%s,%s) RETURNING id",
            (body.name.strip(), body.email)).fetchone()["id"]
        conn.execute(
            "INSERT INTO stage_events(candidate_id,from_stage,to_stage) "
            "VALUES (%s,NULL,'Applied')", (cid,))
    return {"id": cid}

@app.get("/candidates")
def board():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM candidate_current ORDER BY entered_at").fetchall()
    grouped = {s: [] for s in STAGES}
    for r in rows:
        grouped[r["stage"]].append(r)
    return grouped

@app.get("/candidates/{cid}")
def detail(cid: int):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT *, now() - entered_at AS in_stage FROM candidate_current WHERE id=%s",
            (cid,)).fetchone()
        if not cur:
            raise HTTPException(404, "Candidate not found.")
        history = conn.execute(
            "SELECT * FROM stage_events WHERE candidate_id=%s ORDER BY id", (cid,)).fetchall()
    cur["days_in_stage"] = cur.pop("in_stage").total_seconds() / 86400
    return {"candidate": cur, "history": history}

@app.post("/candidates/{cid}/move")
def move(cid: int, body: Move):
    with get_conn() as conn:
        # Lock the row so two simultaneous moves can't both pass validation
        if not conn.execute("SELECT 1 FROM candidates WHERE id=%s FOR UPDATE", (cid,)).fetchone():
            raise HTTPException(404, "Candidate not found.")
        current = conn.execute(
            "SELECT to_stage FROM stage_events WHERE candidate_id=%s ORDER BY id DESC LIMIT 1",
            (cid,)).fetchone()["to_stage"]
        error = validate_move(current, body.to)
        if error:
            raise HTTPException(422, error)
        conn.execute(
            "INSERT INTO stage_events(candidate_id,from_stage,to_stage,note) VALUES (%s,%s,%s,%s)",
            (cid, current, body.to, body.note))
    return {"ok": True}

# no PUT/DELETE for events, by design (mount static last)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
```

**Check:** `docker compose up --build`, open `http://localhost:8000/docs`, and add and move a few candidates by hand.

---

## Step 7: API and immutability tests

`tests/test_api.py` with FastAPI's `TestClient` against a test database:
- Create a candidate, and it appears in "Applied"
- Skip a stage, and you get a 422 with a message
- Move Hired → anything, and you get a 422
- History has one entry per move, in order
- **Immutability:** run raw `UPDATE`/`DELETE`/`TRUNCATE` on `stage_events` and assert an exception

For simplicity, run tests against the compose Postgres and clean up with `TRUNCATE candidates CASCADE`. That works because the TRUNCATE trigger is only on `stage_events`, but it will actually fail due to the trigger on cascade. Better: use a unique name per test and don't truncate.

---

## Step 8: Search parser (the main part)

`app/search.py`, part 1: parsing only, with no DB.

```python
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]
S = "(" + "|".join(STAGES) + ")"
DAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
STOP = r"\b(everyone|everybody|candidates?|who|is|are|was|has|have|been|the|a|an|and|for|in|at|stage|show|find|me)\b"

@dataclass
class Filters:
    name: str = ""
    include: list = field(default_factory=list)
    exclude: list = field(default_factory=list)
    ever_reached: str | None = None
    not_hired: bool = False
    min_days: float | None = None
    moved_to: str | None = None
    since: datetime | None = None
    errors: list = field(default_factory=list)

def resolve_since(word: str, now: datetime) -> datetime:
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if word == "yesterday":
        return today - timedelta(days=1)
    if word == "today":
        return today
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", word):
        return datetime.fromisoformat(word).replace(tzinfo=now.tzinfo)
    # most recent such weekday; if today IS that weekday, use today (documented choice)
    back = (today.weekday() - DAYS.index(word)) % 7
    return today - timedelta(days=back)

def parse_query(raw: str, now: datetime) -> Filters:
    f = Filters()
    q = (raw or "").lower().strip()
    if not q:
        f.errors.append("Type something to search, e.g. 'sharma in screening'.")
        return f

    def take(rx, fn):
        nonlocal q
        def sub(m):
            fn(m); return " "
        q = re.sub(rx, sub, q)

    take(rf"reached (?:the )?{S}(?: stage)?(\s+but\s+(?:not|never|didn'?t get)\s+hired)?",
         lambda m: (setattr(f, "ever_reached", m[1]), setattr(f, "not_hired", bool(m[2]))))
    take(rf"moved to {S}", lambda m: setattr(f, "moved_to", m[1]))
    take(r"since (monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|\d{4}-\d{2}-\d{2})",
         lambda m: setattr(f, "since", resolve_since(m[1], now)))
    take(r"(?:more than|over|longer than)\s+(a|an|\d+)\s*(day|week)s?",
         lambda m: setattr(f, "min_days",
                           (1 if m[1] in ("a", "an") else int(m[1])) * (7 if m[2] == "week" else 1)))
    take(r"\bstuck\b", lambda m: setattr(f, "min_days", f.min_days or 7))
    take(rf"(?:except|excluding|without|not)\s+{S}", lambda m: f.exclude.append(m[1]))
    take(rf"\b(?:in|at|stage)\s+{S}", lambda m: f.include.append(m[1]))

    bad = re.search(r"\bstage\s+(\w+)", q)
    if bad:
        f.errors.append(f"'{bad[1]}' is not a stage. Valid stages: {', '.join(STAGES)}.")

    # bare stage words ("hired and rejected", "interview")
    for s in STAGES:
        if re.search(rf"\b{s}\b", q):
            f.include.append(s)
            q = re.sub(rf"\b{s}\b", " ", q)

    f.name = re.sub(r"\s+", " ", re.sub(STOP, " ", q)).strip()

    # validation
    if len(set(f.include)) > 1:
        f.errors.append("A candidate can only be in one stage at a time, but you asked for "
                        + " and ".join(sorted(set(f.include))) + ". Try 'or' logic by searching separately.")
    for s in set(f.include) & set(f.exclude):
        f.errors.append(f"You both include and exclude '{s}'.")
    if f.since and not f.moved_to:
        f.errors.append("'since <date>' needs an action, e.g. 'moved to interview since monday'.")
    if f.min_days is not None and f.min_days <= 0:
        f.errors.append("Duration must be greater than zero.")
    if f.since and f.since > now:
        f.errors.append("That date is in the future.")
    return f
```

**Test it with an injected `now`** (e.g. a fixed Thursday), one test per example query plus the error cases.

---

## Step 9: Fuzzy matching and ranking

Same file, part 2. Write your own Damerau-Levenshtein (a good interview talking point), with transposition counted as 1 edit:

```python
def dl_distance(a: str, b: str) -> int:
    d = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1): d[i][0] = i
    for j in range(len(b)+1): d[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            cost = 0 if a[i-1] == b[j-1] else 1
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
            if i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:
                d[i][j] = min(d[i][j], d[i-2][j-2]+1)
    return d[-1][-1]

def name_score(query: str, name: str) -> int:
    """0 = no match. Higher is better."""
    if not query:
        return 1                      # no name given: everyone passes the name step
    q, n = query.lower(), name.lower()
    if q == n: return 100
    tokens = n.split()
    if any(t == q for t in tokens) or n.startswith(q): return 80
    if q in n: return 60
    best = 0
    for qt in q.split():
        for t in tokens:
            allowed = 1 if len(qt) <= 4 else 2
            dist = dl_distance(qt, t)
            if dist <= allowed:
                best = max(best, 50 - dist * 10)
    return best
```

Sanity check: `dl_distance("sharam", "sharma")` should be **1**. Put that in a test.

---

## Step 10: Search endpoint (SQL filters, then Python scoring)

Let SQL do the filtering with parameters and score names in Python. The dataset is small, so this is simple and testable.

```python
# in main.py
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from .search import parse_query, name_score

TZ = ZoneInfo(os.environ.get("APP_TZ", "UTC"))

@app.get("/search")
def search(q: str = ""):
    now = datetime.now(TZ)
    f = parse_query(q, now)
    if f.errors:
        raise HTTPException(422, {"errors": f.errors})

    where, params = ["1=1"], []
    if f.include:
        where.append("cc.stage = ANY(%s)"); params.append([s.capitalize() for s in f.include])
    if f.exclude:
        where.append("NOT (cc.stage = ANY(%s))"); params.append([s.capitalize() for s in f.exclude])
    if f.min_days is not None:
        where.append("cc.entered_at <= now() - make_interval(days => %s)"); params.append(f.min_days)
        where.append("cc.stage NOT IN ('Hired','Rejected')")   # "stuck" only applies to active candidates
    if f.ever_reached:
        where.append("EXISTS (SELECT 1 FROM stage_events e WHERE e.candidate_id=cc.id AND e.to_stage=%s)")
        params.append(f.ever_reached.capitalize())
        if f.not_hired: where.append("cc.stage <> 'Hired'")
    if f.moved_to:
        sql = "EXISTS (SELECT 1 FROM stage_events e WHERE e.candidate_id=cc.id AND e.to_stage=%s"
        params.append(f.moved_to.capitalize())
        if f.since:
            sql += " AND e.occurred_at >= %s"; params.append(f.since)
        where.append(sql + ")")

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT cc.*, extract(epoch FROM now()-cc.entered_at)/86400 AS days_in_stage "
            f"FROM candidate_current cc WHERE {' AND '.join(where)}", params).fetchall()

    results = []
    for r in rows:
        score = name_score(f.name, r["name"])
        if f.name and score == 0:
            continue
        bonus = 10 * sum(bool(x) for x in (f.include, f.exclude, f.ever_reached, f.moved_to, f.min_days))
        results.append({**r, "score": score + bonus})
    results.sort(key=lambda r: (-r["score"], -r["days_in_stage"]))

    return {"interpreted_as": describe(f), "count": len(results), "results": results,
            "message": None if results else f"No candidates match ({describe(f)})."}
```

Write a small `describe(f)` that returns text like `name ≈ "sharma", stage = Screening, in stage > 7 days`. Always showing the interpretation is a big usability win.

Note: `"stuck in Screening"` and `"in Screening > 7 days"` both exclude finished candidates. Document that in the README.

---

## Step 11: Minimal UI

`app/static/index.html`, with vanilla JS and `fetch`:
1. Search box at the top. On Enter, call `/search?q=`, show the "interpreted as" line, show errors in red (the 422 `detail.errors`), and show the "no match" message when the list is empty.
2. Board: 5 columns plus Rejected, loaded from `GET /candidates`.
3. Each card has a **Next** button and a **Reject** button. On a 422, show the server's message.
4. Click a card to open a detail panel with history and "X days in Screening".
5. An "Add candidate" form.

---

## Step 12: Seed data and a demo script

Add `scripts/seed.py` that creates about 10 candidates. To test "stuck for a week" and "since Monday" you need old timestamps, so insert events with explicit `occurred_at` values. This is allowed because the triggers only block UPDATE and DELETE, not INSERT.

---

## Step 13: Deliverables

1. **README.md:** how to run (`docker compose up --build`, then open `localhost:8000`), key decisions (derived stage, DB triggers, rule-based parser, timezone choice, "stuck" semantics), limitations, and what you'd do with more time (auth/"who moved it" actor, pagination, `pg_trgm` index for large data, OR queries, richer date phrases).
2. **`chat_logs/`:** export this conversation as markdown and commit it.
3. **The "I disagreed with the AI" section.** One real example from this conversation: the AI's first parser used a loose regex for durations and treated `sharam` as Levenshtein distance 2, so you'd verify and use Damerau-Levenshtein (distance 1) instead. Another: the AI's draft of the test cleanup suggested `TRUNCATE`, which your own trigger blocks. Pick one you genuinely tested and write: *AI suggested → why I disagreed → what I did.*
4. **PDF (1–2 pages):** GitHub link, an architecture diagram (Browser → FastAPI → PostgreSQL, with the parser/scorer box and the trigger-protected `stage_events` table), and 5–6 bullets on decisions.

---

## Suggested order and time plan

| Order | Steps | Done when |
|---|---|---|
| 1 | 1–3 | `docker compose up db` works, triggers block UPDATE |
| 2 | 4–7 | API works in `/docs`, tests pass |
| 3 | 8–9 | parser and fuzzy tests pass, no DB needed |
| 4 | 10–12 | search works end-to-end with seed data |
| 5 | 11, 13 | UI, README, PDF, chat logs |

If you want, I can generate the actual files for any step (starting with `init.sql`, `pipeline.py`, and their tests), so you can run them and then explain every line in the interview.