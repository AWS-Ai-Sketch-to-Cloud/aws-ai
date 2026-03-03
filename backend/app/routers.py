from fastapi import APIRouter, File, UploadFile, Body
from typing import List
from app.models import ArchitectureAnalysisResponse, LogAnalysisResponse, ChatRequest, ChatResponse
from app.services import analyze_diagram_with_bedrock, analyze_logs_with_bedrock, get_ai_consulting_response, get_infrastructure_state
from app.terraform_runner import deploy_terraform, destroy_terraform, rollback_terraform

router = APIRouter(
    prefix="/api/v1/diagram",
    tags=["Architecture Diagram API"]
)

@router.post("/analyze", response_model=ArchitectureAnalysisResponse)
async def upload_diagram(file: UploadFile = File(...)):
    """Receives diagram and returns AI analysis/terraform code."""
    image_bytes = await file.read()
    response = analyze_diagram_with_bedrock(image_bytes, file.filename)
    return response

@router.post("/save-terraform")
async def save_terraform(tf_code: str = Body(..., embed=True)):
    with open("main.tf", "w", encoding="utf-8") as f:
        f.write(tf_code)
    return {"status": "success", "message": "Saved to main.tf"}

@router.post("/deploy")
async def trigger_deploy():
    """Triggers terraform init and apply."""
    return deploy_terraform()

@router.post("/destroy")
async def trigger_destroy():
    """Triggers terraform destroy."""
    return destroy_terraform()

@router.post("/rollback")
async def trigger_rollback():
    """Triggers terraform rollback to previous state backup."""
    return rollback_terraform()

@router.get("/resources")
async def get_resources():
    """Lists current infrastructure resources in LocalStack."""
    return get_infrastructure_state()

@router.post("/logs/analyze", response_model=LogAnalysisResponse)
async def analyze_logs(logs: str = Body(..., embed=True)):
    """Analyzes logs using AI."""
    return analyze_logs_with_bedrock(logs)

@router.post("/chat", response_model=ChatResponse)
async def ai_consultating(request: ChatRequest):
    """AI Consultant chatbot endpoint."""
    return get_ai_consulting_response(request.message, request.current_context)
