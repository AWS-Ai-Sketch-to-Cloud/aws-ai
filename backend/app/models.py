from typing import List, Optional
from pydantic import BaseModel

class ResourceCostEstimate(BaseModel):
    resource_type: str
    estimated_monthly_cost: float
    description: str

class SecurityVulnerability(BaseModel):
    severity: str # High, Medium, Low
    issue: str
    recommendation: str

class ArchitectureAnalysisResponse(BaseModel):
    terraform_code: str
    cost_estimates: List[ResourceCostEstimate]
    total_estimated_cost: float
    security_vulnerabilities: List[SecurityVulnerability]
    explanation: str

class LogAnalysisResponse(BaseModel):
    error_reason: str
    solution: str
    raw_logs: str
    severity: str

class ChatRequest(BaseModel):
    message: str
    current_context: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
