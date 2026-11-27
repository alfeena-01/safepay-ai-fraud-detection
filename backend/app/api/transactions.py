import asyncio
import logging
from threading import Lock
from datetime import datetime, timezone
from uuid import uuid4
from weakref import WeakKeyDictionary

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, joinedload

from app.database.connection import SessionLocal, get_db
from app.database.models import Alert, RiskAssessment, Transaction
from app.database.schemas import (
    RiskRead,
    SimulatorStart,
    TransactionBatchIngest,
    TransactionIngest,
    TransactionRead,
)
from app.services.account_behavior import analyze_sender_behavior
from app.services.anomaly_detection_engine.anomaly_detector import (
    detect_transaction_anomaly,
    train_anomaly_model,
)
from app.services.anomaly_detection_engine.model import ModelUnavailableError
from app.services.anomaly_detection_engine.risk_scoring import assess_transaction
from app.services.auth_security import require_roles

router = APIRouter(prefix="/transactions", tags=["transactions"])
logger = logging.getLogger(__name__)

_simulator_task: asyncio.Task[None] | None = None
_simulator_state: dict[str, object] = {
    "status": "stopped",
    "scenario": None,
    "interval_seconds": None,
    "generated": 0,
    "last_transaction_id": None,
    "last_error": None,
}
_anomaly_model_cache: WeakKeyDictionary[Engine, dict] = WeakKeyDictionary()
_anomaly_model_lock = Lock()
ANOMALY_TRAINING_SAMPLE_SIZE = 5000
MINIMUM_ANOMALY_TRAINING_ROWS = 50


def _persist_events(
    db: Session,
    events: list[TransactionIngest],
    source: str,
) -> list[dict[str, object]]:
    first_index_by_id: dict[str, int] = {}
    duplicate_indexes: set[int] = set()
    for index, event in enumerate(events):
        if event.transaction_id in first_index_by_id:
            duplicate_indexes.add(index)
        else:
            first_index_by_id[event.transaction_id] = index

    transaction_ids = list(first_index_by_id)
    existing_ids = set(
        db.scalars(
            select(Transaction.transaction_id).where(
                Transaction.transaction_id.in_(transaction_ids)
            )
        ).all()
    )
    duplicate_indexes.update(
        index
        for transaction_id, index in first_index_by_id.items()
        if transaction_id in existing_ids
    )
    to_insert = [
        (index, events[index])
        for transaction_id, index in first_index_by_id.items()
        if transaction_id not in existing_ids
    ]

    def transaction_from_event(event: TransactionIngest) -> Transaction:
        return Transaction(
            transaction_id=event.transaction_id,
            step=event.step,
            transaction_type=event.transaction_type,
            amount=event.amount,
            name_orig=event.name_orig,
            old_balance_org=event.old_balance_org,
            new_balance_orig=event.new_balance_orig,
            name_dest=event.name_dest,
            old_balance_dest=event.old_balance_dest,
            new_balance_dest=event.new_balance_dest,
            created_at=event.created_at or datetime.now(timezone.utc),
            source=source,
        )

    if to_insert:
        db.add_all([transaction_from_event(event) for _, event in to_insert])
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            candidate_ids = {event.transaction_id for _, event in to_insert}
            concurrently_inserted = set(
                db.scalars(
                    select(Transaction.transaction_id).where(
                        Transaction.transaction_id.in_(candidate_ids)
                    )
                ).all()
            )
            if not concurrently_inserted:
                raise
            duplicate_indexes.update(
                index
                for index, event in to_insert
                if event.transaction_id in concurrently_inserted
            )
            remaining = [
                (index, event)
                for index, event in to_insert
                if event.transaction_id not in concurrently_inserted
            ]
            if remaining:
                db.add_all([transaction_from_event(event) for _, event in remaining])
                db.commit()

    inserted_indexes = set(first_index_by_id.values()) - duplicate_indexes
    return [
        {
            "transaction_id": event.transaction_id,
            "inserted": index in inserted_indexes,
            "duplicate": index in duplicate_indexes,
            "source": source,
            "analysis_status": "not_analyzed",
        }
        for index, event in enumerate(events)
    ]


def _transaction_record(transaction: Transaction) -> dict[str, object]:
    return {
        "transaction_id": transaction.transaction_id,
        "step": transaction.step,
        "type": transaction.transaction_type,
        "amount": transaction.amount,
        "oldbalanceOrg": transaction.old_balance_org,
        "newbalanceOrig": transaction.new_balance_orig,
        "oldbalanceDest": transaction.old_balance_dest,
        "newbalanceDest": transaction.new_balance_dest,
    }


def _get_anomaly_model(db: Session, current_transaction_pk: int) -> dict | None:
    bind = db.get_bind()
    with _anomaly_model_lock:
        cached = _anomaly_model_cache.get(bind)
        if cached is not None:
            return cached
        history = db.scalars(
            select(Transaction)
            .where(
                Transaction.source == "csv",
                Transaction.id < current_transaction_pk,
            )
            .order_by(Transaction.id.desc())
            .limit(ANOMALY_TRAINING_SAMPLE_SIZE)
        ).all()
        if len(history) < MINIMUM_ANOMALY_TRAINING_ROWS:
            return None
        bundle = train_anomaly_model(
            [_transaction_record(transaction) for transaction in history],
            contamination=0.01,
            random_state=42,
        )
        _anomaly_model_cache[bind] = bundle
        return bundle


def _assessment_result(db: Session, transaction: Transaction) -> dict:
    result = assess_transaction(transaction)
    anomaly_bundle = _get_anomaly_model(db, transaction.id)
    if anomaly_bundle is None:
        anomaly_status = "insufficient_history"
        anomaly_score = 0.0
        anomaly_reason = (
            "At least 50 historical CSV transactions are required to train "
            "the independent Isolation Forest baseline."
        )
    else:
        anomaly = detect_transaction_anomaly(
            _transaction_record(transaction),
            anomaly_bundle,
        )
        anomaly_status = "available"
        anomaly_score = float(anomaly["anomaly_score"])
        anomaly_reason = str(anomaly["anomaly_reason"])

    behavior = analyze_sender_behavior(
        db,
        transaction.name_orig,
        float(transaction.amount),
        current_transaction_pk=transaction.id,
    )
    result.update(
        anomaly_score=anomaly_score,
        anomaly_status=anomaly_status,
        anomaly_reason=anomaly_reason,
        behavior_status=behavior["status"],
        behavior_findings=behavior["findings"],
    )
    explanation_parts = [str(result["explanation"])]
    explanation_parts.append(f"Independent anomaly signal ({anomaly_status}): {anomaly_reason}")
    if behavior["status"] == "insufficient_history":
        explanation_parts.append(
            f"Sender behavior comparison unavailable: only {behavior['history_count']} "
            "prior outgoing transactions; at least 5 are needed."
        )
    elif behavior["status"] == "unavailable":
        explanation_parts.append("Sender behavior comparison unavailable: sender account is missing.")
    else:
        explanation_parts.extend(behavior["findings"])
        if not behavior["findings"]:
            explanation_parts.append(
                "No sender amount deviation met the documented 5x-median review threshold."
            )
    result["explanation"] = "\n".join(explanation_parts)
    return result


def _save_assessment(
    db: Session,
    transaction: Transaction,
    *,
    create_alert: bool = False,
) -> RiskAssessment:
    result = _assessment_result(db, transaction)
    assessment = db.scalar(
        select(RiskAssessment).where(RiskAssessment.transaction_id == transaction.id)
    )
    if assessment is None:
        assessment = RiskAssessment(transaction_id=transaction.id, **result)
        db.add(assessment)
    else:
        for key, value in result.items():
            setattr(assessment, key, value)
    if create_alert and result["risk_level"] == "high":
        _ensure_high_risk_alert(db, transaction, result["risk_level"])
    db.commit()
    db.refresh(assessment)
    return assessment


def _ensure_high_risk_alert(
    db: Session,
    transaction: Transaction,
    risk_level: str,
) -> bool:
    if risk_level != "high":
        return False
    existing_alert = db.scalar(
        select(Alert.id).where(Alert.transaction_id == transaction.id)
    )
    if existing_alert is not None:
        return False
    db.add(
        Alert(
            transaction_id=transaction.id,
            title="High-risk transaction requires review",
            severity="high",
        )
    )
    return True


def _assess_ingested_event(db: Session, result: dict[str, object]) -> dict[str, object]:
    transaction = db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.risk_assessment))
        .where(Transaction.transaction_id == result["transaction_id"])
    )
    if transaction is None:
        raise RuntimeError("Persisted transaction could not be retrieved.")
    if transaction.risk_assessment is None:
        try:
            assessment = _save_assessment(db, transaction, create_alert=True)
        except ModelUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": str(exc),
                    "transaction_id": transaction.transaction_id,
                    "stored": True,
                },
            ) from exc
    else:
        assessment = transaction.risk_assessment
        if _ensure_high_risk_alert(db, transaction, assessment.risk_level):
            db.commit()
    return {
        **result,
        "analysis_status": "complete",
        "risk_assessment": RiskRead.model_validate(assessment).model_dump(mode="json"),
    }


def _simulated_event(scenario: str, sequence: int) -> TransactionIngest:
    is_suspicious_scenario = scenario == "suspicious" or (
        scenario == "mixed" and sequence % 5 == 0
    )
    if is_suspicious_scenario:
        amount = 75_000.0 + (sequence % 5) * 2_500
        old_balance = 12_000.0
        transaction_type = "TRANSFER"
    else:
        amount = float(25 + (sequence * 173) % 4_975)
        old_balance = amount + 1_000.0
        transaction_type = "PAYMENT"
    return TransactionIngest(
        transaction_id=f"demo-{uuid4().hex}",
        step=sequence,
        transaction_type=transaction_type,
        amount=amount,
        name_orig=f"demo-sender-{sequence % 8 + 1}",
        old_balance_org=old_balance,
        new_balance_orig=max(old_balance - amount, 0.0),
        name_dest=f"demo-receiver-{sequence % 5 + 1}",
        old_balance_dest=500.0,
        new_balance_dest=500.0 + amount,
        created_at=datetime.now(timezone.utc),
    )


async def _run_simulator(interval_seconds: float, scenario: str) -> None:
    sequence = int(_simulator_state["generated"])
    try:
        while True:
            sequence += 1
            event = _simulated_event(scenario, sequence)
            try:
                with SessionLocal() as db:
                    result = _persist_events(db, [event], "simulator")[0]
                    _simulator_state.update(
                        generated=int(_simulator_state["generated"]) + 1,
                        last_transaction_id=event.transaction_id,
                    )
                    transaction = db.scalar(
                        select(Transaction).where(
                            Transaction.transaction_id == event.transaction_id
                        )
                    )
                    if transaction is not None:
                        _save_assessment(db, transaction, create_alert=True)
            except SQLAlchemyError as exc:
                _simulator_state.update(
                    status="error",
                    last_error="Could not save a simulated transaction.",
                )
                logger.error("Simulator transaction persistence failed: %s", type(exc).__name__)
                return
            except ModelUnavailableError:
                _simulator_state.update(
                    status="error",
                    last_error="Fraud model unavailable; demo event was stored without assessment.",
                )
                logger.error("Simulator stopped because the fraud model is unavailable.")
                return
            await asyncio.sleep(interval_seconds)
    finally:
        if _simulator_state["status"] == "running":
            _simulator_state["status"] = "stopped"


async def shutdown_simulator() -> None:
    global _simulator_task
    if _simulator_task is not None and not _simulator_task.done():
        _simulator_task.cancel()
        try:
            await _simulator_task
        except asyncio.CancelledError:
            pass
    _simulator_task = None
    if _simulator_state["status"] == "running":
        _simulator_state["status"] = "stopped"


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    q: str | None = None,
    transaction_type: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    fraud_only: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Transaction).options(joinedload(Transaction.risk_assessment))
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(
            Transaction.transaction_id.ilike(term),
            Transaction.name_orig.ilike(term),
            Transaction.name_dest.ilike(term),
        ))
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type.upper())
    if fraud_only is not None:
        query = query.where(
            Transaction.label_known.is_(True),
            Transaction.is_fraud.is_(fraud_only),
        )
    if risk_level:
        query = query.join(RiskAssessment).where(RiskAssessment.risk_level == risk_level)
    return db.scalars(query.order_by(Transaction.id.desc()).offset(offset).limit(limit)).unique().all()


@router.post("/ingest")
def ingest_transaction(
    payload: TransactionIngest,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    result = _persist_events(db, [payload], "external")[0]
    return _assess_ingested_event(db, result)


@router.post("/ingest/batch")
def ingest_transaction_batch(
    payload: TransactionBatchIngest,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    results = _persist_events(db, payload.transactions, "external")
    analyzed = [_assess_ingested_event(db, result) for result in results]
    inserted = sum(bool(result["inserted"]) for result in results)
    return {
        "received": len(analyzed),
        "inserted": inserted,
        "duplicates_skipped": len(analyzed) - inserted,
        "analyzed": sum(result["analysis_status"] == "complete" for result in analyzed),
        "transactions": analyzed,
    }


@router.get("/live")
def list_live_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    transactions = db.scalars(
        select(Transaction).options(joinedload(Transaction.risk_assessment))
        .where(Transaction.source != "csv")
        .order_by(Transaction.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            **TransactionRead.model_validate(transaction).model_dump(mode="json"),
            "risk_assessment": (
                RiskRead.model_validate(transaction.risk_assessment).model_dump(mode="json")
                if transaction.risk_assessment
                else None
            ),
        }
        for transaction in transactions
    ]


@router.post("/simulator/start")
async def start_simulator(
    payload: SimulatorStart,
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    global _simulator_task
    if _simulator_task is not None and not _simulator_task.done():
        raise HTTPException(status_code=409, detail="The transaction simulator is already running.")
    _simulator_state.update(
        status="running",
        scenario=payload.scenario,
        interval_seconds=payload.interval_seconds,
        generated=0,
        last_transaction_id=None,
        last_error=None,
    )
    _simulator_task = asyncio.create_task(
        _run_simulator(payload.interval_seconds, payload.scenario)
    )
    return {"status": "running", **_simulator_state}


@router.post("/simulator/stop")
async def stop_simulator(
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    await shutdown_simulator()
    return {"status": _simulator_state["status"], **_simulator_state}


@router.get("/simulator/status")
def get_simulator_status(
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    return dict(_simulator_state)


@router.post("/analyze-batch")
def analyze_historical_batch(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_roles("admin", "analyst")),
):
    transactions = db.scalars(
        select(Transaction)
        .outerjoin(RiskAssessment, RiskAssessment.transaction_id == Transaction.id)
        .where(Transaction.source == "csv", RiskAssessment.id.is_(None))
        .order_by(Transaction.id)
        .limit(limit)
    ).all()
    assessments = []
    for transaction in transactions:
        try:
            assessment = _save_assessment(db, transaction, create_alert=True)
        except ModelUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": str(exc),
                    "transaction_id": transaction.transaction_id,
                    "stored": True,
                },
            ) from exc
        assessments.append(
            {
                "transaction_id": transaction.transaction_id,
                "risk_level": assessment.risk_level,
                "fraud_probability": assessment.fraud_probability,
                "anomaly_score": assessment.anomaly_score,
                "anomaly_status": assessment.anomaly_status,
            }
        )
    return {"analyzed": len(assessments), "transactions": assessments}


@router.get("/{transaction_id}")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.scalar(
        select(Transaction).options(joinedload(Transaction.risk_assessment)).where(Transaction.id == transaction_id)
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    result = TransactionRead.model_validate(transaction).model_dump(mode="json")
    result["risk_assessment"] = RiskRead.model_validate(transaction.risk_assessment).model_dump(mode="json") \
        if transaction.risk_assessment else None
    return result


@router.post("/{transaction_id}/analyze", response_model=RiskRead)
def analyze_transaction(transaction_id: int, db: Session = Depends(get_db), _identity: dict = Depends(require_roles("admin", "analyst"))):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    try:
        return _save_assessment(db, transaction, create_alert=True)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc