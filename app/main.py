from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import candidates_router, search_router, config_router

app = FastAPI(title="Mini Hiring Pipeline")

# Include Routers
app.include_router(config_router)
app.include_router(candidates_router)
app.include_router(search_router)

# Mount static files last (no PUT/DELETE for events by design)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
