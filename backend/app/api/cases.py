from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import InvestigationCase, Transaction
from app.database.schemas import CaseCreate, CaseRead, CaseUpdate, NoteCreate

router = APIRouter(prefix="/cases", tags=["investigation cases"])


@router.get("/", response_model=list[CaseRead])
def list_cases(status: str | None = None, db: Session = Depends(get_db)):
    query = select(InvestigationCase).order_by(InvestigationCase.updated_at.desc())
    if status:
        if status not in {"open", "in_progress", "closed"}:
            raise HTTPException(status_code=422, detail="Invalid case status.")
        query = query.where(InvestigationCase.status == status)
    return db.scalars(query).all()


@router.post("/", response_model=CaseRead, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    if payload.transaction_id is not None and db.get(Transaction, payload.transaction_id) is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    case = InvestigationCase(
        case_number=f"SP-{uuid4().hex[:8].upper()}",
        **payload.model_dump(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("transaction_id") is not None and db.get(Transaction, updates["transaction_id"]) is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    for key, value in updates.items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/notes", response_model=CaseRead)
def add_case_note(case_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    case.notes = f"{case.notes}\n{payload.note}".strip()
    db.commit()
    db.refresh(case)
    return case