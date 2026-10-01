import os
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hiring_db"
)


def seed():
    print(f"Connecting to database: {DATABASE_URL}")
    now = datetime.now(timezone.utc)

    # Calculate reference timestamps
    t_minus_14d = now - timedelta(days=14)
    t_minus_12d = now - timedelta(days=12)
    t_minus_10d = now - timedelta(days=10)
    t_minus_8d = now - timedelta(days=8)
    t_minus_5d = now - timedelta(days=5)
    t_minus_3d = now - timedelta(days=3)
    t_minus_1d = now - timedelta(days=1)
    t_today = now - timedelta(hours=2)

    # Find this past Monday
    days_since_monday = (now.weekday() - 0) % 7
    monday_dt = (now - timedelta(days=days_since_monday)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )

    candidates_data = [
        {
            "name": "Rohit Sharma",
            "email": "rohit.sharma@example.com",
            "created_at": t_minus_14d,
            "events": [
                (None, "Applied", t_minus_14d, "Applied via LinkedIn"),
                ("Applied", "Screening", t_minus_10d, "Resume looks great"),
                ("Screening", "Interview", monday_dt, "Passed technical phone screen"),
            ],
        },
        {
            "name": "Pooja Patel",
            "email": "pooja.patel@example.com",
            "created_at": t_minus_14d,
            "events": [
                (None, "Applied", t_minus_14d, "Direct application"),
                ("Applied", "Screening", t_minus_10d, "Screening passed"),
                ("Screening", "Interview", t_minus_8d, "System design round completed"),
                ("Interview", "Offer", t_minus_3d, "Competitive offer extended"),
            ],
        },
        {
            "name": "Aarav Gupta",
            "email": "aarav.gupta@example.com",
            "created_at": t_minus_14d,
            "events": [
                (None, "Applied", t_minus_14d, "Referral by Dev Lead"),
                ("Applied", "Screening", t_minus_10d, "Initial screen complete"),
                ("Screening", "Interview", t_minus_8d, "Technical interviews completed"),
                ("Interview", "Offer", t_minus_5d, "Offer extended"),
                ("Offer", "Hired", t_minus_1d, "Offer accepted! Start date confirmed."),
            ],
        },
        {
            "name": "Vikram Malhotra",
            "email": "vikram.m@example.com",
            "created_at": t_minus_10d,
            "events": [
                (None, "Applied", t_minus_10d, "Applied via Careers Portal"),
                ("Applied", "Screening", t_minus_8d, "Screening call"),
                ("Screening", "Rejected", t_minus_5d, "Position requires more senior experience"),
            ],
        },
        {
            "name": "Ananya Desai",
            "email": "ananya.d@example.com",
            "created_at": t_minus_10d,
            "events": [
                (None, "Applied", t_minus_10d, "Portfolio submission"),
                ("Applied", "Screening", t_minus_8d, "Stuck in screening for over 8 days"),
            ],
        },
        {
            "name": "Rahul Verma",
            "email": "rahul.v@example.com",
            "created_at": t_minus_14d,
            "events": [
                (None, "Applied", t_minus_14d, "Applied for Backend Lead"),
                ("Applied", "Screening", t_minus_12d, "Screened"),
                ("Screening", "Interview", t_minus_10d, "Stuck in interview stage > 7 days"),
            ],
        },
        {
            "name": "Sneha Kulkarni",
            "email": "sneha.k@example.com",
            "created_at": t_minus_5d,
            "events": [
                (None, "Applied", t_minus_5d, "Inbound application"),
                ("Applied", "Screening", t_minus_1d, "Recruiter screen scheduled"),
            ],
        },
        {
            "name": "Karan Singhania",
            "email": "karan.s@example.com",
            "created_at": t_minus_14d,
            "events": [
                (None, "Applied", t_minus_14d, "Applied"),
                ("Applied", "Screening", t_minus_10d, "Screened"),
                ("Screening", "Interview", t_minus_8d, "Final round attended"),
                ("Interview", "Rejected", t_minus_3d, "Reached interview stage but rejected"),
            ],
        },
        {
            "name": "Meera Iyer",
            "email": "meera.iyer@example.com",
            "created_at": t_today,
            "events": [
                (None, "Applied", t_today, "New applicant today"),
            ],
        },
        {
            "name": "Devendra Joshi",
            "email": "dev.joshi@example.com",
            "created_at": t_minus_3d,
            "events": [
                (None, "Applied", t_minus_3d, "Applied on Tuesday"),
                ("Applied", "Screening", monday_dt, "Moved to screening this week"),
            ],
        },
    ]

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            print("Seeding candidates and historical events...")
            for c in candidates_data:
                cur.execute(
                    "INSERT INTO candidates (name, email, created_at) VALUES (%s, %s, %s) RETURNING id",
                    (c["name"], c["email"], c["created_at"]),
                )
                cid = cur.fetchone()["id"]

                for from_st, to_st, occ_at, note in c["events"]:
                    cur.execute(
                        "INSERT INTO stage_events (candidate_id, from_stage, to_stage, occurred_at, note) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (cid, from_st, to_st, occ_at, note),
                    )
            conn.commit()

    print(f"Successfully seeded {len(candidates_data)} candidates with audit histories!")


if __name__ == "__main__":
    seed()
