from datetime import datetime
from pydantic import BaseModel


# Candidate Request & Response Schemas
class NewCandidate(BaseModel):
    name: str
    email: str | None = None


class CandidateCreatedResponse(BaseModel):
    id: int


class CandidateSummary(BaseModel):
    id: int
    name: str
    email: str | None = None
    stage: str
    entered_at: datetime
    days_in_stage: float | None = None


class StageEventResponse(BaseModel):
    id: int
    candidate_id: int
    from_stage: str | None = None
    to_stage: str
    occurred_at: datetime
    note: str | None = None


class CandidateDetail(CandidateSummary):
    days_in_stage: float


class CandidateDetailResponse(BaseModel):
    candidate: CandidateDetail
    history: list[StageEventResponse]


class Move(BaseModel):
    to: str
    note: str | None = None


class MoveResponse(BaseModel):
    ok: bool


# Search Schemas
class SearchCandidateResult(CandidateSummary):
    days_in_stage: float
    score: float


class SearchResponse(BaseModel):
    interpreted_as: str
    count: int
    results: list[SearchCandidateResult]
    message: str | None = None


# Config Schemas
class ConfigResponse(BaseModel):
    stages: list[str]
    allowed_transitions: dict[str, str]
    final_stages: list[str]
    timezone: str
