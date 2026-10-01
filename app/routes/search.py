import os
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter
from ..db import get_conn
from ..logger import logger
from ..exceptions import SearchQueryException
from ..search import parse_query, name_score, describe
from ..schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])

TZ = ZoneInfo(os.environ.get("APP_TZ", "UTC"))


@router.get("", response_model=SearchResponse)
def search(q: str = ""):
    now = datetime.now(TZ)
    f = parse_query(q, now)
    if f.errors:
        logger.warning("Search query rejected: '%s' (errors: %s)", q, f.errors)
        raise SearchQueryException(f.errors)

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
