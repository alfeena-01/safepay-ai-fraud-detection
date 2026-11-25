from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import InvestigationCase, InvestigationReport, RiskAssessment, Transaction
from app.database.schemas import ReportCreate, ReportRead

router = APIRouter(prefix="/reports", tags=["investigation reports"])


@router.get("/", response_model=list[ReportRead])
def list_reports(db: Session = Depends(get_db)):
    return db.scalars(select(InvestigationReport).order_by(InvestigationReport.created_at.desc())).all()


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(InvestigationReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.post("/", response_model=ReportRead, status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)):
    case = db.get(InvestigationCase, payload.case_id) if payload.case_id is not None else None
    transaction = db.get(Transaction, payload.transaction_id) if payload.transaction_id is not None else None
    if payload.case_id is not None and case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if payload.transaction_id is not None and transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    content = payload.content
    if not content:
        summary = [f"Investigation: {payload.title}"]
        if case:
            summary.extend([
                f"Case: {case.case_number} — {case.status} ({case.priority} priority)",
                f"Case description: {case.description or 'No description supplied.'}",
                f"Investigation notes: {case.notes or 'No notes recorded.'}",
            ])
        if transaction:
            risk = db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id == transaction.id))
            summary.extend([
                f"Transaction: {transaction.transaction_id}",
                f"Type and amount: {transaction.transaction_type} / {transaction.amount:.2f}",
                f"Recorded fraud label: {'yes' if transaction.is_fraud else 'no'}",
                f"Risk assessment: {risk.risk_level} ({risk.overall_risk_score:.1f}/100)"
                if risk else "Risk assessment: not yet performed.",
            ])
        content = "\n\n".join(summary)
    report = InvestigationReport(
        case_id=payload.case_id,
        transaction_id=payload.transaction_id,
        title=payload.title,
        content=content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report