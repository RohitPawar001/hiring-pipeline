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


def dl_distance(a: str, b: str) -> int:
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def name_score(query: str, name: str) -> int:
    """0 = no match. Higher is better."""
    if not query:
        return 1  # no name given: everyone passes the name step
    q, n = query.lower(), name.lower()
    if q == n:
        return 100
    tokens = n.split()
    if any(t == q for t in tokens) or n.startswith(q):
        return 80
    if q in n:
        return 60
    best = 0
    for qt in q.split():
        for t in tokens:
            allowed = 1 if len(qt) <= 4 else 2
            dist = dl_distance(qt, t)
            if dist <= allowed:
                best = max(best, 50 - dist * 10)
    return best


def describe(f: Filters) -> str:
    """Produce a human-readable summary of the interpreted filter."""
    parts = []
    if f.name:
        parts.append(f'name ≈ "{f.name}"')
    if f.include:
        parts.append(f"stage = {', '.join(s.capitalize() for s in f.include)}")
    if f.exclude:
        parts.append(f"stage ≠ {', '.join(s.capitalize() for s in f.exclude)}")
    if f.min_days is not None:
        days_str = f"{int(f.min_days)} days" if f.min_days.is_integer() else f"{f.min_days} days"
        parts.append(f"in stage > {days_str}")
    if f.ever_reached:
        reached_str = f"reached {f.ever_reached.capitalize()}"
        if f.not_hired:
            reached_str += " (not hired)"
        parts.append(reached_str)
    if f.moved_to:
        moved_str = f"moved to {f.moved_to.capitalize()}"
        if f.since:
            moved_str += f" since {f.since.strftime('%Y-%m-%d')}"
        parts.append(moved_str)
    return ", ".join(parts) if parts else "all candidates"
