import csv
import hashlib
import io
import math
from collections.abc import Iterator
from typing import BinaryIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.database.models import RiskAssessment, Transaction
from app.services.auth_security import require_roles

router = APIRouter(prefix="/dataset", tags=["dataset"])

REQUIRED_COLUMNS = {"type", "amount", "nameorig", "namedest"}
MISSING_VALUES = {"", "na", "n/a", "nan", "null", "none", "missing"}
BATCH_SIZE = 500


def _optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return None if cleaned.lower() in MISSING_VALUES else cleaned


def _number(row: dict[str, str], key: str, row_number: int, integer: bool = False):
    value = (row.get(key) or "").strip()
    if value.lower() in MISSING_VALUES:
        return None if integer else 0.0
    try:
        parsed = float(value)
        if not math.isfinite(parsed) or parsed < 0 or (integer and not parsed.is_integer()):
            raise ValueError
        return int(parsed) if integer else parsed
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {key} value at CSV row {row_number}.") from exc


def _fraud_label(row: dict[str, str], row_number: int) -> tuple[bool, bool]:
    value = (row.get("isfraud") or "").strip().lower()
    if value in MISSING_VALUES:
        return False, False
    if value in {"1", "true", "yes"}:
        return True, True
    if value in {"0", "false", "no"}:
        return False, True
    raise HTTPException(
        status_code=422,
        detail=f"Invalid isFraud label at CSV row {row_number}.",
    )


def _records(file: BinaryIO, upload_key: str) -> Iterator[dict]:
    file.seek(0)
    text = io.TextIOWrapper(file, encoding="utf-8-sig", newline="")
    try:
        reader = csv.DictReader(text)
        if not reader.fieldnames:
            raise HTTPException(status_code=422, detail="CSV has no header row.")
        normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
        missing = sorted(REQUIRED_COLUMNS - normalized.keys())
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing required CSV columns: {', '.join(missing)}.")
        for row_number, source_row in enumerate(reader, start=2):
            row = {key: (source_row.get(original) or "").strip() for key, original in normalized.items()}
            source_id = _optional_text(row.get("transactionid")) or f"csv-{upload_key}-{row_number}"
            if len(source_id) > 128:
                raise HTTPException(status_code=422, detail=f"Transaction ID is too long at CSV row {row_number}.")
            transaction_type = (_optional_text(row.get("type")) or "UNKNOWN").upper()
            if len(transaction_type) > 32:
                raise HTTPException(status_code=422, detail=f"Transaction type is too long at CSV row {row_number}.")
            fraud_label, label_known = _fraud_label(row, row_number)
            yield {
                "transaction_id": source_id,
                "step": _number(row, "step", row_number, integer=True),
                "transaction_type": transaction_type,
                "amount": _number(row, "amount", row_number),
                "name_orig": _optional_text(row.get("nameorig")),
                "old_balance_org": _number(row, "oldbalanceorg", row_number),
                "new_balance_orig": _number(row, "newbalanceorig", row_number),
                "name_dest": _optional_text(row.get("namedest")),
                "old_balance_dest": _number(row, "oldbalancedest", row_number),
                "new_balance_dest": _number(row, "newbalancedest", row_number),
                "is_fraud": fraud_label,
                "label_known": label_known,
                "is_flagged_fraud": (row.get("isflaggedfraud") or "0").lower() in {"1", "true", "yes"},
            }
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8 encoded.") from exc
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="CSV contains malformed rows.") from exc
    finally:
        text.detach()


def _insert_batch(db: Session, rows: list[dict]) -> tuple[int, int]:
    batch_ids: set[str] = set()
    unique_rows = []
    duplicate_count = 0
    for row in rows:
        if row["transaction_id"] in batch_ids:
            duplicate_count += 1
        else:
            batch_ids.add(row["transaction_id"])
            unique_rows.append(row)
    existing = set(db.scalars(
        select(Transaction.transaction_id).where(Transaction.transaction_id.in_(batch_ids))
    ).all())
    new_rows = [row for row in unique_rows if row["transaction_id"] not in existing]
    duplicate_count += len(unique_rows) - len(new_rows)
    if new_rows:
        db.execute(insert(Transaction), new_rows)
    return len(new_rows), duplicate_count


@router.post("/upload")
def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db), _identity: dict = Depends(require_roles("admin", "analyst"))):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file.")
    file.file.seek(0, io.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="CSV exceeds the configured upload limit.")
    upload_key = hashlib.file_digest(file.file, "sha256").hexdigest()[:16]
    validated_rows = sum(1 for _ in _records(file.file, upload_key))
    if not validated_rows:
        raise HTTPException(status_code=422, detail="CSV contains no transaction rows.")
    batch: list[dict] = []
    inserted = 0
    duplicate_count = 0
    try:
        for row in _records(file.file, upload_key):
            batch.append(row)
            if len(batch) == BATCH_SIZE:
                added, duplicates = _insert_batch(db, batch)
                inserted += added
                duplicate_count += duplicates
                batch.clear()
        if batch:
            added, duplicates = _insert_batch(db, batch)
            inserted += added
            duplicate_count += duplicates
        db.commit()
    except (HTTPException, SQLAlchemyError):
        db.rollback()
        raise
    return {
        "filename": file.filename,
        "rows_validated": validated_rows,
        "inserted": inserted,
        "duplicates_skipped": duplicate_count,
        "missing_values_defaulted": True,
        "message": "Blank amounts and balances default to 0; blank account IDs are stored as null.",
    }


@router.get("/summary")
def dataset_summary(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Transaction.id))) or 0
    labeled = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.label_known.is_(True))
    ) or 0
    fraud_count = db.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.label_known.is_(True),
            Transaction.is_fraud.is_(True),
        )
    ) or 0
    amount_total = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0))) or 0.0
    return {
        "total_transactions": total,
        "labeled_transactions": labeled,
        "fraud_transactions": fraud_count,
        "legitimate_transactions": labeled - fraud_count,
        "fraud_rate": round(fraud_count / labeled, 6) if labeled else 0.0,
        "total_amount": round(amount_total, 2),
    }