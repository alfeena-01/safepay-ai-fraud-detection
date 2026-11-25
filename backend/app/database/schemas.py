from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: str
    step: int | None
    transaction_type: str
    amount: float
    name_orig: str | None
    name_dest: str | None
    is_fraud: bool
    is_flagged_fraud: bool
    created_at: datetime


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fraud_probability: float
    anomaly_score: float
    graph_risk: float
    overall_risk_score: float
    risk_level: str
    explanation: str
    recommended_action: str
    model_version: str
    assessed_at: datetime


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=10000)
    transaction_id: int | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    assigned_to: str | None = Field(default=None, max_length=128)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = Field(default=None, pattern="^(open|in_progress|closed)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    assigned_to: str | None = Field(default=None, max_length=128)


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    transaction_id: int | None
    title: str
    description: str
    status: str
    priority: str
    assigned_to: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class ReportCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    case_id: int | None = None
    transaction_id: int | None = None
    content: str | None = Field(default=None, max_length=20000)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int | None
    transaction_id: int | None
    title: str
    content: str
    created_at: datetime