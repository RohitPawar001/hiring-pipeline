from fastapi import HTTPException, status


class PipelineException(HTTPException):
    """Base application exception with consistent status code and message."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str | dict | list = "An application error occurred.",
    ):
        super().__init__(status_code=status_code, detail=detail)


class CandidateNotFoundException(PipelineException):
    def __init__(self, candidate_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID #{candidate_id} not found.",
        )


class InvalidStageTransitionException(PipelineException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )


class InvalidCandidateDataException(PipelineException):
    def __init__(self, message: str = "Name is required."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )


class SearchQueryException(PipelineException):
    def __init__(self, errors: list[str]):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors},
        )


class DatabaseConnectionException(PipelineException):
    def __init__(self, message: str = "Database service unavailable."):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )
