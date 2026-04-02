from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.constants import CONTRACT_VERSION


class SessionCreateApiRequest(BaseModel):
    inputType: Literal["TEXT", "SKETCH", "TEXT_WITH_SKETCH"] = "TEXT"
    inputText: str | None = None
    inputImageUrl: str | None = None


class SessionCreateApiResponse(BaseModel):
    sessionId: str
    projectId: str
    versionNo: int
    status: str
    createdAt: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionListItem(BaseModel):
    sessionId: str
    versionNo: int
    inputType: str
    status: str
    createdAt: str
    updatedAt: str


class SessionListResponse(BaseModel):
    items: list[SessionListItem]
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    inputText: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices("inputText", "input_text"))
    inputType: Literal["text", "sketch"] = Field(
        default="text",
        validation_alias=AliasChoices("inputType", "input_type"),
    )
    inputImageDataUrl: str | None = Field(
        default=None,
        validation_alias=AliasChoices("inputImageDataUrl", "input_image_data_url"),
    )


class ArchitectureSaveRequest(BaseModel):
    schemaVersion: str = "v1"
    architectureJson: dict[str, Any]


class TerraformGenerateResponse(BaseModel):
    sessionId: str
    status: str
    validationStatus: str
    terraformCode: str
    validationOutput: str | None = None
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class CostCalculateResponse(BaseModel):
    sessionId: str
    status: str
    currency: str
    region: str
    monthlyTotal: float
    costBreakdownJson: dict[str, Any]
    assumptionJson: dict[str, Any]
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class UploadImageRequest(BaseModel):
    contentType: str = Field(min_length=3, max_length=100)
    fileName: str = Field(min_length=1, max_length=255)


class UploadImageResponse(BaseModel):
    fileId: str
    url: str
    contentType: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionStatusPatchRequest(BaseModel):
    status: Literal[
        "CREATED",
        "ANALYZING",
        "ANALYZED",
        "GENERATING_TERRAFORM",
        "GENERATED",
        "COST_CALCULATED",
        "FAILED",
    ]
    errorCode: str | None = Field(default=None, max_length=50)
    errorMessage: str | None = Field(default=None, max_length=2000)


class SessionStatusPatchResponse(BaseModel):
    sessionId: str
    status: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionResultResponse(BaseModel):
    sessionId: str
    status: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionDetailArchitecture(BaseModel):
    schemaVersion: str
    architectureJson: dict[str, Any]


class SessionDetailTerraform(BaseModel):
    validationStatus: str
    terraformCode: str
    validationOutput: str | None = None


class SessionDetailCost(BaseModel):
    currency: str
    region: str
    assumptionJson: dict[str, Any]
    monthlyTotal: float
    costBreakdownJson: dict[str, Any]


class SessionDetailError(BaseModel):
    code: str | None = None
    message: str | None = None


class SessionDetailResponse(BaseModel):
    sessionId: str
    projectId: str
    versionNo: int
    inputType: str
    inputText: str | None = None
    inputImageUrl: str | None = None
    status: str
    architecture: SessionDetailArchitecture | None = None
    terraform: SessionDetailTerraform | None = None
    cost: SessionDetailCost | None = None
    error: SessionDetailError | None = None
    createdAt: str
    updatedAt: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionCompareSummary(BaseModel):
    sessionId: str
    versionNo: int
    status: str
    createdAt: str


class JsonDiffItem(BaseModel):
    path: str
    changeType: Literal["added", "removed", "changed"]
    before: Any | None = None
    after: Any | None = None


class TerraformDiffResponse(BaseModel):
    changed: bool
    diff: str


class CostFieldDelta(BaseModel):
    before: float | None = None
    after: float | None = None
    delta: float | None = None


class CostDiffResponse(BaseModel):
    changed: bool
    monthlyTotal: CostFieldDelta
    breakdown: dict[str, CostFieldDelta]
    assumptionsChanged: list[JsonDiffItem]


class SessionCompareResponse(BaseModel):
    baseSession: SessionCompareSummary
    targetSession: SessionCompareSummary
    jsonDiff: list[JsonDiffItem]
    terraformDiff: TerraformDiffResponse
    costDiff: CostDiffResponse
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class DeployRequest(BaseModel):
    awsRegion: str | None = Field(default=None, max_length=30)
    simulate: bool = False


class DestroyRequest(BaseModel):
    awsRegion: str | None = Field(default=None, max_length=30)
    simulate: bool = False
    confirmDestroy: bool = False
    confirmationCode: str | None = Field(default=None, min_length=4, max_length=100)


class SessionDeploymentItem(BaseModel):
    deploymentId: str
    action: str
    status: str
    region: str
    startedAt: str | None = None
    completedAt: str | None = None
    createdAt: str
    log: str | None = None
    appliedResources: dict[str, Any] | None = None


class SessionDeploymentResponse(BaseModel):
    item: SessionDeploymentItem
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class SessionDeploymentListResponse(BaseModel):
    items: list[SessionDeploymentItem]
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class ErrorPayload(BaseModel):
    code: Literal["PARSE_ERROR", "SCHEMA_ERROR", "TIMEOUT_ERROR", "INTERNAL_ERROR"]
    message: str


class AnalysisMeta(BaseModel):
    provider: Literal["bedrock", "local_fallback"]
    modelId: str | None = None
    usedImage: bool
    fallbackUsed: bool
    requirementCoverage: float | None = None
    unmetHints: list[str] | None = None
    rationale: dict[str, Any] | None = None


class AnalyzeResponse(BaseModel):
    sessionId: str
    status: Literal["generated", "failed"]
    parsedJson: dict[str, Any] | None = None
    analysisMeta: AnalysisMeta | None = None
    error: ErrorPayload | None = None
    contractVersion: Literal["v2"] = CONTRACT_VERSION
