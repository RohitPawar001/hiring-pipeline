import uuid
import pytest
import psycopg
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn


client = TestClient(app)


def unique_name(prefix="Candidate"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_get_config():
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "stages" in data
    assert "allowed_transitions" in data
    assert "final_stages" in data
    assert "timezone" in data
    assert "Applied" in data["stages"]


def test_create_candidate_appears_in_applied():
    name = unique_name("Alice")
    email = f"{name.lower()}@example.com"
    
    # Create candidate
    resp = client.post("/candidates", json={"name": name, "email": email})
    assert resp.status_code == 201
    cid = resp.json()["id"]

    # Verify candidate appears in 'Applied' on the board
    board_resp = client.get("/candidates")
    assert board_resp.status_code == 200
    board = board_resp.json()
    applied_candidates = [c for c in board["Applied"] if c["id"] == cid]
    assert len(applied_candidates) == 1
    assert applied_candidates[0]["name"] == name
    assert applied_candidates[0]["email"] == email


def test_skip_stage_fails_with_422():
    name = unique_name("Bob")
    resp = client.post("/candidates", json={"name": name, "email": "bob@example.com"})
    assert resp.status_code == 201
    cid = resp.json()["id"]

    # Trying to skip from 'Applied' straight to 'Interview' or 'Offer'
    skip_resp = client.post(f"/candidates/{cid}/move", json={"to": "Interview"})
    assert skip_resp.status_code == 422
    assert "Cannot move Applied" in skip_resp.json()["detail"]


def test_move_hired_to_anything_fails_with_422():
    name = unique_name("Charlie")
    resp = client.post("/candidates", json={"name": name, "email": "charlie@example.com"})
    cid = resp.json()["id"]

    # Walk candidate to Hired
    for next_stage in ["Screening", "Interview", "Offer", "Hired"]:
        move_resp = client.post(f"/candidates/{cid}/move", json={"to": next_stage})
        assert move_resp.status_code == 200

    # Moving from Hired to any other stage should fail with 422
    invalid_move = client.post(f"/candidates/{cid}/move", json={"to": "Interview"})
    assert invalid_move.status_code == 422
    assert "final outcome" in invalid_move.json()["detail"]

    # Rejecting an already hired candidate should also fail
    reject_move = client.post(f"/candidates/{cid}/move", json={"to": "Rejected"})
    assert reject_move.status_code == 422
    assert "final outcome" in reject_move.json()["detail"]


def test_history_has_one_entry_per_move_in_order():
    name = unique_name("Diana")
    resp = client.post("/candidates", json={"name": name, "email": "diana@example.com"})
    cid = resp.json()["id"]

    moves = [
        {"to": "Screening", "note": "Passed initial resume screen"},
        {"to": "Interview", "note": "Tech round scheduled"},
        {"to": "Offer", "note": "Offer extended"},
    ]

    for m in moves:
        move_resp = client.post(f"/candidates/{cid}/move", json=m)
        assert move_resp.status_code == 200

    # Retrieve details and history
    detail_resp = client.get(f"/candidates/{cid}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    history = data["history"]

    # 1 initial 'Applied' event + 3 moves = 4 events
    assert len(history) == 4
    assert history[0]["from_stage"] is None
    assert history[0]["to_stage"] == "Applied"

    assert history[1]["from_stage"] == "Applied"
    assert history[1]["to_stage"] == "Screening"
    assert history[1]["note"] == "Passed initial resume screen"

    assert history[2]["from_stage"] == "Screening"
    assert history[2]["to_stage"] == "Interview"
    assert history[2]["note"] == "Tech round scheduled"

    assert history[3]["from_stage"] == "Interview"
    assert history[3]["to_stage"] == "Offer"
    assert history[3]["note"] == "Offer extended"


def test_db_immutability_triggers():
    # Insert candidate & event to test immutability
    name = unique_name("Eve")
    resp = client.post("/candidates", json={"name": name, "email": "eve@example.com"})
    cid = resp.json()["id"]

    # Raw UPDATE on stage_events must raise an exception
    with get_conn() as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="stage_events is append-only"):
            conn.execute("UPDATE stage_events SET note='tampered' WHERE candidate_id=%s", (cid,))

    # Raw DELETE on stage_events must raise an exception
    with get_conn() as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="stage_events is append-only"):
            conn.execute("DELETE FROM stage_events WHERE candidate_id=%s", (cid,))

    # Raw TRUNCATE on stage_events must raise an exception
    with get_conn() as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="stage_events is append-only"):
            conn.execute("TRUNCATE TABLE stage_events")


def test_search_endpoint():
    unique_suffix = uuid.uuid4().hex[:6]
    name1 = f"Rohit Sharma {unique_suffix}"
    name2 = f"Pooja Patel {unique_suffix}"
    
    c1 = client.post("/candidates", json={"name": name1, "email": "rohit@example.com"}).json()["id"]
    c2 = client.post("/candidates", json={"name": name2, "email": "pooja@example.com"}).json()["id"]

    client.post(f"/candidates/{c1}/move", json={"to": "Screening"})

    # Search with name and stage
    res = client.get(f"/search?q=sharma in screening").json()
    assert res["count"] >= 1
    assert any(r["id"] == c1 for r in res["results"])
    assert 'name ≈ "sharma"' in res["interpreted_as"]
    assert "stage = Screening" in res["interpreted_as"]

    # Fuzzy search with typo
    res_fuzzy = client.get(f"/search?q=sharam").json()
    assert res_fuzzy["count"] >= 1
    assert any(r["id"] == c1 for r in res_fuzzy["results"])
