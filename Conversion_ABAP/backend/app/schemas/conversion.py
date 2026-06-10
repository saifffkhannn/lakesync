"""Shared Pydantic schemas for conversion, validation, review, and pipeline results."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Supported Snowflake artifact categories emitted by the converter."""

    VIEW = "view"
    PROCEDURE = "procedure"
    TASK = "task"
    DYNAMIC_TABLE = "dynamic_table"
    SCRIPT = "script"


class ReviewDecision(StrEnum):
    """Human review outcomes for generated conversion results."""

    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    RERUN = "rerun"


class ConversionRequest(BaseModel):
    """Input payload for one ABAP conversion request."""

    request_id: UUID = Field(default_factory=uuid4)
    source_name: str
    source_type: str
    abap_source: str
    package_name: str | None = None
    target_database: str | None = None
    target_schema: str | None = None
    submitted_by: str


class AstNode(BaseModel):
    """One parsed ABAP AST node with optional child nodes and annotations."""

    node_type: str
    value: str
    line: int
    children: list["AstNode"] = Field(default_factory=list)
    annotations: dict[str, Any] = Field(default_factory=dict)


class ParsedProgram(BaseModel):
    """Parser output used by rules, metadata enrichment, and AI prompts."""

    ast: AstNode
    control_flow_graph: dict[str, list[str]]
    dependency_graph: dict[str, list[str]]
    annotations: dict[str, Any]


class SemanticContext(BaseModel):
    """SAP metadata, relationship, function, and memory context for conversion."""

    tables: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[dict[str, Any]] = Field(default_factory=list)
    domains: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    function_signatures: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_patterns: list[dict[str, Any]] = Field(default_factory=list)


class RuleResult(BaseModel):
    """Record of one deterministic rewrite applied before AI conversion."""

    rule_name: str
    before: str
    after: str
    confidence_delta: float


class ConversionOutput(BaseModel):
    """Generated SQL plus confidence, warnings, assumptions, notes, and applied rules."""

    sql: str
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    conversion_notes: list[str] = Field(default_factory=list)
    artifact_type: ArtifactType = ArtifactType.SCRIPT
    applied_rules: list[RuleResult] = Field(default_factory=list)


class ValidationStatus(StrEnum):
    """Validation outcome used by each pipeline validation stage."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ValidationResult(BaseModel):
    """Result of one syntax, semantic, object, execution, or confidence check."""

    stage: str
    status: ValidationStatus
    message: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    """Complete conversion response returned by the API pipeline."""

    request_id: UUID
    output: ConversionOutput
    validations: list[ValidationResult]
    auto_approved: bool
    review_required: bool
    deployed_version: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewAction(BaseModel):
    """Reviewer action submitted from the review portal or API."""

    request_id: UUID
    decision: ReviewDecision
    reviewer: str
    edited_sql: str | None = None
    comments: str | None = None


AstNode.model_rebuild()
