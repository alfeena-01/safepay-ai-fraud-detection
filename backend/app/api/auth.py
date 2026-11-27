from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.services.auth_security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=password_hash, role="analyst")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    try:
        token = create_access_token(user.id, user.role)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}}

@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    identity = getattr(request.state, "identity", None)
    if not identity:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = db.get(User, int(identity["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable.")
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}
