from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, cases, dashboard, dataset, graph, predictions, reports, transactions
from app.core.config import settings
from app.database.connection import Base, engine
from app.database import models  # noqa: F401

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Transaction monitoring and investigation API for SafePay.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (dashboard.router, dataset.router, transactions.router, predictions.router, alerts.router,
               graph.router, cases.router, reports.router):
    app.include_router(router, prefix="/api")
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.app_name}