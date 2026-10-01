import os
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .db import get_conn
from .pipeline import validate_move, STAGES
from .search import parse_query, name_score, describe

TZ = ZoneInfo(os.environ.get("APP_TZ", "UTC"))

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


@app.get("/search")
def search(q: str = ""):
    now = datetime.now(TZ)
    f = parse_query(q, now)
    if f.errors:
        raise HTTPException(422, {"errors": f.errors})

    where, params = ["1=1"], []
    if f.include:
        where.append("cc.stage = ANY(%s)")
        params.append([s.capitalize() for s in f.include])
    if f.exclude:
        where.append("NOT (cc.stage = ANY(%s))")
        params.append([s.capitalize() for s in f.exclude])
    if f.min_days is not None:
        where.append("cc.entered_at <= now() - make_interval(days => %s)")
        params.append(f.min_days)
        where.append("cc.stage NOT IN ('Hired','Rejected')")  # "stuck" only applies to active candidates
    if f.ever_reached:
        where.append(
            "EXISTS (SELECT 1 FROM stage_events e WHERE e.candidate_id=cc.id AND e.to_stage=%s)"
        )
        params.append(f.ever_reached.capitalize())
        if f.not_hired:
            where.append("cc.stage <> 'Hired'")
    if f.moved_to:
        sql = "EXISTS (SELECT 1 FROM stage_events e WHERE e.candidate_id=cc.id AND e.to_stage=%s"
        params.append(f.moved_to.capitalize())
        if f.since:
            sql += " AND e.occurred_at >= %s"
            params.append(f.since)
        where.append(sql + ")")

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT cc.*, extract(epoch FROM now()-cc.entered_at)/86400 AS days_in_stage "
            f"FROM candidate_current cc WHERE {' AND '.join(where)}",
            params,
        ).fetchall()

    results = []
    for r in rows:
        score = name_score(f.name, r["name"])
        if f.name and score == 0:
            continue
        bonus = 10 * sum(
            bool(x)
            for x in (f.include, f.exclude, f.ever_reached, f.moved_to, f.min_days)
        )
        results.append({**r, "score": score + bonus})
    results.sort(key=lambda r: (-r["score"], -r["days_in_stage"]))

    return {
        "interpreted_as": describe(f),
        "count": len(results),
        "results": results,
        "message": None
        if results
        else f"No candidates match ({describe(f)}).",
    }


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
