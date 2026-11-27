from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import alerts, auth, cases, chat, dashboard, dataset, graph, predictions, reports, transactions, member3_intelligence
from app.core.config import settings
from app.database.connection import Base, engine, migrate_schema
from app.database import models  # noqa: F401
from app.database.connection import SessionLocal
from app.database.models import User
from app.services.auth_security import hash_password, decode_access_token
from app.api.transactions import shutdown_simulator

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        public = path in {"/health", "/docs", "/redoc", "/openapi.json"} or path in {"/api/auth/login", "/api/auth/register"}
        if request.method == "OPTIONS" or public or getattr(request.app.state, "auth_disabled", False):
            return await call_next(request)
        authorization = request.headers.get("Authorization", "")
        token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
        identity = decode_access_token(token) if token else None
        if not identity:
            return JSONResponse(status_code=401, content={"detail": "Authentication required or session expired."})
        request.state.identity = identity
        return await call_next(request)

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema(engine)
    admin_email = settings.admin_email.strip().lower()
    admin_password = settings.admin_password
    if admin_email and admin_password:
        with SessionLocal() as db:
            existing = db.query(User).filter(User.email == admin_email).first()
            if existing is None:
                db.add(User(email=admin_email, full_name=settings.admin_name,
                            password_hash=hash_password(admin_password), role="admin"))
                db.commit()
    try:
        yield
    finally:
        await shutdown_simulator()


app = FastAPI(
    title=settings.app_name,
    description="Transaction monitoring and investigation API for SafePay.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuthenticationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, dashboard.router, dataset.router, transactions.router, predictions.router, alerts.router, member3_intelligence.router,
               graph.router, cases.router, reports.router, chat.router):
    app.include_router(router, prefix="/api")
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.app_name}