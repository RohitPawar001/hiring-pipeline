from fastapi import APIRouter
from ..db import get_conn
from ..logger import logger
from ..exceptions import (
    CandidateNotFoundException,
    InvalidCandidateDataException,
    InvalidStageTransitionException,
)
from ..pipeline import validate_move, STAGES
from ..schemas import (
    NewCandidate,
    CandidateCreatedResponse,
    CandidateSummary,
    CandidateDetailResponse,
    Move,
    MoveResponse,
)

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("", status_code=201, response_model=CandidateCreatedResponse)
def add_candidate(body: NewCandidate):
    if not body.name.strip():
        logger.warning("Failed candidate creation: name is empty")
        raise InvalidCandidateDataException("Name is required.")
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
    logger.info("Created candidate #%s (%s)", cid, body.name.strip())
    return {"id": cid}


@router.get("", response_model=dict[str, list[CandidateSummary]])
def board():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT *, extract(epoch FROM now() - entered_at) / 86400 AS days_in_stage "
            "FROM candidate_current ORDER BY entered_at"
        ).fetchall()
    grouped = {s: [] for s in STAGES}
    for r in rows:
        grouped[r["stage"]].append(r)
    logger.debug("Fetched board candidates count: %d", len(rows))
    return grouped


@router.get("/{cid}", response_model=CandidateDetailResponse)
def detail(cid: int):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT *, now() - entered_at AS in_stage FROM candidate_current WHERE id=%s",
            (cid,),
        ).fetchone()
        if not cur:
            logger.warning("Candidate detail lookup failed: #%s not found", cid)
            raise CandidateNotFoundException(cid)
        history = conn.execute(
            "SELECT * FROM stage_events WHERE candidate_id=%s ORDER BY id",
            (cid,),
        ).fetchall()
    cur["days_in_stage"] = cur.pop("in_stage").total_seconds() / 86400
    logger.debug("Fetched detail for candidate #%s (%d events)", cid, len(history))
    return {"candidate": cur, "history": history}


@router.post("/{cid}/move", response_model=MoveResponse)
def move(cid: int, body: Move):
    with get_conn() as conn:
        # Lock the row so two simultaneous moves can't both pass validation
        if not conn.execute(
            "SELECT 1 FROM candidates WHERE id=%s FOR UPDATE", (cid,)
        ).fetchone():
            logger.warning("Candidate move failed: #%s not found", cid)
            raise CandidateNotFoundException(cid)
        current = conn.execute(
            "SELECT to_stage FROM stage_events WHERE candidate_id=%s ORDER BY id DESC LIMIT 1",
            (cid,),
        ).fetchone()["to_stage"]
        error = validate_move(current, body.to)
        if error:
            logger.warning("Invalid transition attempt for candidate #%s: %s", cid, error)
            raise InvalidStageTransitionException(error)
        conn.execute(
            "INSERT INTO stage_events(candidate_id,from_stage,to_stage,note) VALUES (%s,%s,%s,%s)",
            (cid, current, body.to, body.note),
        )
    logger.info("Transitioned candidate #%s: %s -> %s", cid, current, body.to)
    return {"ok": True}
