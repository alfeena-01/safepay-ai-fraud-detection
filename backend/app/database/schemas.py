from datetime import datetime, timezone

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class RiskAssessmentSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fraud_probability: float
    model_classification: str
    classification_threshold: float
    overall_risk_score: float
    risk_level: str


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
    label_known: bool
    is_flagged_fraud: bool
    created_at: datetime
    source: str
    risk_assessment: RiskAssessmentSummaryRead | None = None


class TransactionIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("transaction_id", "transactionId"),
    )
    step: int | None = Field(default=None, ge=0)
    transaction_type: str = Field(
        min_length=1,
        max_length=32,
        validation_alias=AliasChoices("transaction_type", "type"),
    )
    amount: float = Field(ge=0, allow_inf_nan=False)
    name_orig: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("name_orig", "nameOrig"),
    )
    old_balance_org: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        validation_alias=AliasChoices("old_balance_org", "oldbalanceOrg"),
    )
    new_balance_orig: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        validation_alias=AliasChoices("new_balance_orig", "newbalanceOrig"),
    )
    name_dest: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("name_dest", "nameDest"),
    )
    old_balance_dest: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        validation_alias=AliasChoices("old_balance_dest", "oldbalanceDest"),
    )
    new_balance_dest: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        validation_alias=AliasChoices("new_balance_dest", "newbalanceDest"),
    )
    created_at: datetime | None = None

    @field_validator("transaction_id", "transaction_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be blank.")
        return cleaned

    @field_validator("transaction_type")
    @classmethod
    def normalize_transaction_type(cls, value: str) -> str:
        return value.upper()

    @field_validator("name_orig", "name_dest")
    @classmethod
    def normalize_account_id(cls, value: str | None) -> str | None:
        cleaned = value.strip() if value is not None else ""
        return cleaned or None

    @field_validator("created_at")
    @classmethod
    def use_utc_for_naive_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class TransactionBatchIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transactions: list[TransactionIngest] = Field(min_length=1, max_length=500)


class SimulatorStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interval_seconds: float = Field(default=2.0, ge=1.0, le=3600.0, allow_inf_nan=False)
    scenario: str = Field(default="mixed", pattern="^(normal|suspicious|mixed)$")


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fraud_probability: float
    model_classification: str
    classification_threshold: float
    anomaly_score: float
    anomaly_status: str
    anomaly_reason: str
    behavior_status: str
    behavior_findings: list[str]
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