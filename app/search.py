import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]
S = "(" + "|".join(STAGES) + ")"
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
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
            fn(m)
            return " "

        q = re.sub(rx, sub, q)

    take(
        rf"reached (?:the )?{S}(?: stage)?(\s+but\s+(?:not|never|didn'?t get)\s+hired)?",
        lambda m: (
            setattr(f, "ever_reached", m[1]),
            setattr(f, "not_hired", bool(m[2])),
        ),
    )
    take(rf"moved to {S}", lambda m: setattr(f, "moved_to", m[1]))
    take(
        r"since (monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|\d{4}-\d{2}-\d{2})",
        lambda m: setattr(f, "since", resolve_since(m[1], now)),
    )
    take(
        r"(?:more than|over|longer than)\s+(a|an|\d+)\s*(day|week)s?",
        lambda m: setattr(
            f,
            "min_days",
            (1 if m[1] in ("a", "an") else int(m[1])) * (7 if m[2] == "week" else 1),
        ),
    )
    take(r"\bstuck\b", lambda m: setattr(f, "min_days", f.min_days or 7))
    take(rf"(?:except|excluding|without|not)\s+{S}", lambda m: f.exclude.append(m[1]))
    take(rf"\b(?:in|at|stage)\s+{S}", lambda m: f.include.append(m[1]))

    bad = re.search(r"\bstage\s+(\w+)", q)
    if bad:
        f.errors.append(
            f"'{bad[1]}' is not a stage. Valid stages: {', '.join(STAGES)}."
        )

    # bare stage words ("hired and rejected", "interview")
    for s in STAGES:
        if re.search(rf"\b{s}\b", q):
            f.include.append(s)
            q = re.sub(rf"\b{s}\b", " ", q)

    f.name = re.sub(r"\s+", " ", re.sub(STOP, " ", q)).strip()

    # validation
    if len(set(f.include)) > 1:
        f.errors.append(
            "A candidate can only be in one stage at a time, but you asked for "
            + " and ".join(sorted(set(f.include)))
            + ". Try 'or' logic by searching separately."
        )
    for s in set(f.include) & set(f.exclude):
        f.errors.append(f"You both include and exclude '{s}'.")
    if f.since and not f.moved_to:
        f.errors.append(
            "'since <date>' needs an action, e.g. 'moved to interview since monday'."
        )
    if f.min_days is not None and f.min_days <= 0:
        f.errors.append("Duration must be greater than zero.")
    if f.since and f.since > now:
        f.errors.append("That date is in the future.")
    return f
