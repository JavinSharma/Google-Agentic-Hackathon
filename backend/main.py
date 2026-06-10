from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.events import router as events_router

app = FastAPI(title="Hyper Context Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)

@app.get("/")
async def root():
    return {"status": "running"}