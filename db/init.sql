-- Schema initialization for hiring pipeline database

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
