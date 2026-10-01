STAGES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"]
NEXT = {
    "Applied": "Screening",
    "Screening": "Interview",
    "Interview": "Offer",
    "Offer": "Hired",
}
FINAL = {"Hired", "Rejected"}


def validate_move(current: str, target: str) -> str | None:
    """Return an error message, or None if the move is allowed."""
    if target not in STAGES:
        return f"'{target}' is not a valid stage."
    if current in FINAL:
        return f"{current} is a final outcome and cannot change."
    if target == "Rejected":
        return None
    if NEXT.get(current) != target:
        expected = NEXT.get(current)
        return f"Cannot move {current} → {target}. Next stage is {expected}."
    return None
