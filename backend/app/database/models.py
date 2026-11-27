from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    step: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    name_orig: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    old_balance_org: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_balance_orig: Mapped[float | None] = mapped_column(Float, nullable=True)
    name_dest: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    old_balance_dest: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_balance_dest: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    label_known: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    is_flagged_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(
        String(24), default="csv", server_default="csv", nullable=False, index=True
    )

    risk_assessment: Mapped["RiskAssessment | None"] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", uselist=False
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="transaction")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), unique=True)
    fraud_probability: Mapped[float] = mapped_column(Float)
    model_classification: Mapped[str] = mapped_column(
        String(16), default="unknown", server_default="unknown"
    )
    classification_threshold: Mapped[float] = mapped_column(
        Float, default=0.5, server_default="0.5"
    )
    anomaly_score: Mapped[float] = mapped_column(Float)
    anomaly_status: Mapped[str] = mapped_column(
        String(24), default="unavailable", server_default="unavailable"
    )
    anomaly_reason: Mapped[str] = mapped_column(
        Text, default="Not calculated.", server_default="Not calculated."
    )
    behavior_status: Mapped[str] = mapped_column(
        String(24), default="unavailable", server_default="unavailable"
    )
    behavior_findings: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'")
    )
    graph_risk: Mapped[float] = mapped_column(Float)
    overall_risk_score: Mapped[float] = mapped_column(Float, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(255))
    model_version: Mapped[str] = mapped_column(String(64), default="demo-heuristic-v1")
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    transaction: Mapped[Transaction] = relationship(back_populates="risk_assessment")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    transaction: Mapped[Transaction] = relationship(back_populates="alerts")


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    reports: Mapped[list["InvestigationReport"]] = relationship(back_populates="case")


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("investigation_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    case: Mapped[InvestigationCase | None] = relationship(back_populates="reports")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True)
    model_name: Mapped[str] = mapped_column(String(128))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(24), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
