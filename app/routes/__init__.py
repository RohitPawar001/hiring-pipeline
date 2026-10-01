from .candidates import router as candidates_router
from .search import router as search_router
from .config import router as config_router

__all__ = ["candidates_router", "search_router", "config_router"]
