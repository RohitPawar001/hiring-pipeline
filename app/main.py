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
            (body.name.strip(), body.email),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO stage_events(candidate_id,from_stage,to_stage) "
            "VALUES (%s,NULL,'Applied')",
            (cid,),
        )
    return {"id": cid}


@app.get("/candidates")
def board():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM candidate_current ORDER BY entered_at"
        ).fetchall()
    grouped = {s: [] for s in STAGES}
    for r in rows:
        grouped[r["stage"]].append(r)
    return grouped


@app.get("/candidates/{cid}")
def detail(cid: int):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT *, now() - entered_at AS in_stage FROM candidate_current WHERE id=%s",
            (cid,),
        ).fetchone()
        if not cur:
            raise HTTPException(404, "Candidate not found.")
        history = conn.execute(
            "SELECT * FROM stage_events WHERE candidate_id=%s ORDER BY id",
            (cid,),
        ).fetchall()
    cur["days_in_stage"] = cur.pop("in_stage").total_seconds() / 86400
    return {"candidate": cur, "history": history}


@app.post("/candidates/{cid}/move")
def move(cid: int, body: Move):
    with get_conn() as conn:
        # Lock the row so two simultaneous moves can't both pass validation
        if not conn.execute(
            "SELECT 1 FROM candidates WHERE id=%s FOR UPDATE", (cid,)
        ).fetchone():
            raise HTTPException(404, "Candidate not found.")
        current = conn.execute(
            "SELECT to_stage FROM stage_events WHERE candidate_id=%s ORDER BY id DESC LIMIT 1",
            (cid,),
        ).fetchone()["to_stage"]
        error = validate_move(current, body.to)
        if error:
            raise HTTPException(422, error)
        conn.execute(
            "INSERT INTO stage_events(candidate_id,from_stage,to_stage,note) VALUES (%s,%s,%s,%s)",
            (cid, current, body.to, body.note),
        )
    return {"ok": True}


# no PUT/DELETE for events, by design (mount static last)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
