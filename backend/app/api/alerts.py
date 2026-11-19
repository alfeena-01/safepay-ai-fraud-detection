from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import Alert, Transaction

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
def list_alerts(status: str | None = Query(default=None, pattern="^(open|acknowledged|resolved)$"),
                db: Session = Depends(get_db)):
    query = select(Alert).options(joinedload(Alert.transaction)).order_by(Alert.id.desc())
    if status:
        query = query.where(Alert.status == status)
    return [{
        "id": alert.id,
        "transaction_id": alert.transaction_id,
        "transaction_ref": alert.transaction.transaction_id,
        "amount": alert.transaction.amount,
        "title": alert.title,
        "severity": alert.severity,
        "status": alert.status,
        "created_at": alert.created_at,
    } for alert in db.scalars(query).unique().all()]


@router.patch("/{alert_id}")
def update_alert(alert_id: int, status: str, db: Session = Depends(get_db)):
    if status not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=422, detail="Status must be open, acknowledged, or resolved.")
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.status = status
    db.commit()
    return {"id": alert.id, "status": alert.status}