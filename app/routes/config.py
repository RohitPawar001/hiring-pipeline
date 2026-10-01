import os
from zoneinfo import ZoneInfo
from fastapi import APIRouter
from ..pipeline import STAGES, NEXT, FINAL
from ..schemas import ConfigResponse

router = APIRouter(prefix="", tags=["Config"])

TZ = ZoneInfo(os.environ.get("APP_TZ", "UTC"))


@router.get("/config", response_model=ConfigResponse)
def get_config():
    return {
        "stages": STAGES,
        "allowed_transitions": NEXT,
        "final_stages": sorted(list(FINAL)),
        "timezone": str(TZ),
    }
