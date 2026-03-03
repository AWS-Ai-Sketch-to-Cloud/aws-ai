import boto3
import json
import base64
import os
from app.models import ArchitectureAnalysisResponse, LogAnalysisResponse, ChatResponse

# Since we use LocalStack, there is no Bedrock locally available in community edition.
# However, this function is written to simulate or call actual AWS Bedrock.
# To keep "zero cost" while testing locally, we'll implement a mock bypass 
# or use real Bedrock with precise prompt to generate basic tf code. 

bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

def analyze_diagram_with_bedrock(image_bytes: bytes, filename: str) -> ArchitectureAnalysisResponse:
    """
    Analyzes the uploaded architecture diagram using Claude 3.5 Sonnet on AWS Bedrock.
    """
    
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    image_media_type = "image/png"
    if filename.lower().endswith('.jpeg') or filename.lower().endswith('.jpg'):
        image_media_type = "image/jpeg"
        
    prompt = """
    You are an expert AWS Cloud Architect and Terraform developer.
    Analyze the provided AWS architecture diagram.
    Your task is to:
    1. Identify all AWS resources present in the diagram (e.g., VPC, Subnets, EC2, EKS, RDS, S3).
    2. Write the complete Terraform code to provision these resources. Use AWS provider ~> 5.0. 
       - IMPORTANT: Do NOT include NAT Gateways or any expensive resources unless explicitly required to save cost. 
       - Always use t3.micro or equivalent free-tier/low-cost instance types by default.
    3. Estimate the monthly cost of these resources.
    4. Identify any potential security vulnerabilities (e.g., public RDS, missing encryption) and provide recommendations.
    
    Output strictly in the following JSON format without Markdown formatting or extra text:
    {
      "terraform_code": "string containing entire terraform code",
      "cost_estimates": [
        {"resource_type": "string", "estimated_monthly_cost": 0.0, "description": "string"}
      ],
      "total_estimated_cost": 0.0,
      "security_vulnerabilities": [
        {"severity": "High/Medium/Low", "issue": "string", "recommendation": "string"}
      ],
      "explanation": "Brief explanation of the architecture"
    }
    """
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": encoded_image
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        content_text = response_body.get('content')[0].get('text')
        
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
            
        parsed_data = json.loads(content_text)
        return ArchitectureAnalysisResponse(**parsed_data)
        
    except Exception as e:
        print(f"Bedrock invocation failed: {e}. Returning Mock Response.")
        return ArchitectureAnalysisResponse(
            terraform_code='resource "aws_s3_bucket" "mock" { bucket = "mock-bucket" }',
            cost_estimates=[{"resource_type": "S3", "estimated_monthly_cost": 0.0, "description": "Mock storage"}],
            total_estimated_cost=0.0,
            security_vulnerabilities=[],
            explanation="Mocked due to Bedrock execution error: " + str(e)
        )

def analyze_logs_with_bedrock(raw_logs: str) -> LogAnalysisResponse:
    """
    Analyzes server logs using Bedrock to identify the cause of failure and provide a solution.
    """
    prompt = f"""
    You are an expert AWS Site Reliability Engineer.
    I have the following logs from a failing service:
    {raw_logs}
    
    Analayze the logs and identify:
    1. The reason for the error.
    2. A step-by-step solution to fix it.
    3. The severity of the issue.
    
    Output strictly in the following JSON format:
    {{
      "error_reason": "string",
      "solution": "string",
      "raw_logs": "{raw_logs}",
      "severity": "High/Medium/Low"
    }}
    """
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        content_text = response_body.get('content')[0].get('text')
        
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
            
        parsed_data = json.loads(content_text)
        return LogAnalysisResponse(**parsed_data)
        
    except Exception as e:
        return LogAnalysisResponse(
            error_reason="AI 분석 중 오류가 발생했습니다.",
            solution="수동으로 로그를 확인해 주세요.",
            raw_logs=raw_logs,
            severity="Unknown"
        )

def get_ai_consulting_response(message: str, context: str = None) -> ChatResponse:
    """
    AI Cloud Consultant chatbot logic using Bedrock.
    """
    prompt = f"""
    You are an expert AWS Cloud Consultant.
    The user is asking for advice regarding their infrastructure.
    Current Infrastructure Context (if any): {context}
    
    User Question: {message}
    
    Provide helpful, cost-effective, and secure advice. Keep it concise.
    Output strictly in the following JSON format:
    {{
      "reply": "your helpful advice string"
    }}
    """
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        response_body = json.loads(response.get('body').read())
        content_text = response_body.get('content')[0].get('text')
        
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
            
        parsed_data = json.loads(content_text)
        return ChatResponse(**parsed_data)
    except Exception as e:
        return ChatResponse(reply=f"죄송합니다. 현재 상담원이 부재중입니다. (에러: {str(e)})")

def get_infrastructure_state() -> dict:
    """Lists current resources from LocalStack."""
    # List S3 buckets as an example of monitoring
    s3 = boto3.client("s3", endpoint_url="http://localhost:4566", aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    try:
        buckets = s3.list_buckets().get("Buckets", [])
        return {"resources": [{"id": b["Name"], "type": "S3 Bucket", "status": "Running"} for b in buckets]}
    except:
        return {"resources": []}
