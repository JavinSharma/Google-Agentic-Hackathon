import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.limiter import limiter
from backend.routes.events import router as events_router
from backend.routes.query import router as query_router

app = FastAPI(title="Hyper Context Engine API")

# Attach the limiter to the app state so slowapi can find it
app.state.limiter = limiter

# Register the 429 handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate-limiting middleware (must come before CORS so it fires first)
app.add_middleware(SlowAPIMiddleware)

frontend_url = os.getenv("FRONTEND_URL")
allow_origins = [frontend_url] if frontend_url else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(query_router)

@app.get("/")
async def root():
    return {"status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}
