from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.constants import CONTRACT_VERSION


class GitHubRepoItem(BaseModel):
    fullName: str
    name: str
    owner: str
    private: bool
    defaultBranch: str
    htmlUrl: str
    updatedAt: str


class GitHubRepoListResponse(BaseModel):
    repos: list[GitHubRepoItem]
    contractVersion: str = CONTRACT_VERSION


class GitHubRepoAnalyzeRequest(BaseModel):
    fullName: str = Field(min_length=3, max_length=200)


class GitHubRepoAnalyzeResponse(BaseModel):
    fullName: str
    defaultBranch: str
    scannedFileCount: int
    summary: str
    findings: list[str]
    recommendedStack: list[str]
    requiredServices: list[str]
    languageHints: list[str]
    dependencyFiles: list[str]
    deploymentSteps: list[str]
    risks: list[str]
    costNotes: list[str]
    detected: dict[str, bool]
    architectureJson: dict[str, object]
    terraformCode: str
    cost: dict[str, object]
    contractVersion: str = CONTRACT_VERSION
