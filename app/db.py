import os
import psycopg
from psycopg.rows import dict_row


def get_conn():
    db_url = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:5432/hiring")
    return psycopg.connect(db_url, row_factory=dict_row)
