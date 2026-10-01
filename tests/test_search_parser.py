from datetime import datetime, timezone
from app.search import parse_query, resolve_since, Filters, dl_distance, name_score

# Fixed baseline now: Thursday, 2026-10-01 15:00:00 UTC
NOW = datetime(2026, 10, 1, 15, 0, 0, tzinfo=timezone.utc)


def test_empty_query_error():
    f = parse_query("", NOW)
    assert len(f.errors) > 0
    assert "Type something to search" in f.errors[0]

    f_space = parse_query("   ", NOW)
    assert len(f_space.errors) > 0


def test_name_and_stage():
    f = parse_query("sharma in screening", NOW)
    assert f.errors == []
    assert f.name == "sharma"
    assert f.include == ["screening"]


def test_ever_reached_stage():
    f = parse_query("reached interview", NOW)
    assert f.errors == []
    assert f.ever_reached == "interview"
    assert f.not_hired is False


def test_ever_reached_stage_but_not_hired():
    f = parse_query("reached interview but not hired", NOW)
    assert f.errors == []
    assert f.ever_reached == "interview"
    assert f.not_hired is True

    f2 = parse_query("reached the offer stage but didn't get hired", NOW)
    assert f2.errors == []
    assert f2.ever_reached == "offer"
    assert f2.not_hired is True


def test_moved_to_since():
    # Thursday = 2026-10-01. 'since monday' -> 2026-09-28
    f = parse_query("moved to interview since monday", NOW)
    assert f.errors == []
    assert f.moved_to == "interview"
    assert f.since == datetime(2026, 9, 28, 0, 0, 0, tzinfo=timezone.utc)

    # since yesterday -> 2026-09-30
    f_yesterday = parse_query("moved to screening since yesterday", NOW)
    assert f_yesterday.errors == []
    assert f_yesterday.moved_to == "screening"
    assert f_yesterday.since == datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)

    # since YYYY-MM-DD
    f_iso = parse_query("moved to offer since 2026-09-15", NOW)
    assert f_iso.errors == []
    assert f_iso.moved_to == "offer"
    assert f_iso.since == datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)


def test_stuck_and_duration_filters():
    # 'stuck' defaults to 7 days
    f_stuck = parse_query("stuck in interview", NOW)
    assert f_stuck.errors == []
    assert f_stuck.include == ["interview"]
    assert f_stuck.min_days == 7

    # 'more than 3 days'
    f_days = parse_query("in screening more than 3 days", NOW)
    assert f_days.errors == []
    assert f_days.include == ["screening"]
    assert f_days.min_days == 3

    # 'over 2 weeks'
    f_weeks = parse_query("over 2 weeks in applied", NOW)
    assert f_weeks.errors == []
    assert f_weeks.include == ["applied"]
    assert f_weeks.min_days == 14


def test_stage_exclusions():
    f = parse_query("john except rejected", NOW)
    assert f.errors == []
    assert f.name == "john"
    assert f.exclude == ["rejected"]


def test_multiple_conflicting_include_stages_error():
    f = parse_query("hired and rejected", NOW)
    assert len(f.errors) > 0
    assert "A candidate can only be in one stage at a time" in f.errors[0]


def test_simultaneous_include_exclude_error():
    f = parse_query("in screening not screening", NOW)
    assert len(f.errors) > 0
    assert "both include and exclude 'screening'" in f.errors[0]


def test_since_without_action_error():
    f = parse_query("sharma since monday", NOW)
    assert len(f.errors) > 0
    assert "'since <date>' needs an action" in f.errors[0]


def test_invalid_stage_name_error():
    f = parse_query("stage manager", NOW)
    assert len(f.errors) > 0
    assert "'manager' is not a stage" in f.errors[0]


def test_dl_distance_transposition():
    # Transposition of adjacent characters counts as 1 edit in Damerau-Levenshtein
    assert dl_distance("sharam", "sharma") == 1
    assert dl_distance("rohit", "rohit") == 0
    assert dl_distance("rohit", "rohti") == 1
    assert dl_distance("alex", "alxe") == 1


def test_name_scoring():
    # Exact match
    assert name_score("rohit", "rohit") == 100
    # Token or prefix match
    assert name_score("sharma", "rohit sharma") == 80
    assert name_score("roh", "rohit") == 80
    # Substring match
    assert name_score("har", "sharma") == 60
    # Fuzzy transposition match
    assert name_score("sharam", "rohit sharma") > 0
    # Empty query matches everyone
    assert name_score("", "any candidate") == 1
