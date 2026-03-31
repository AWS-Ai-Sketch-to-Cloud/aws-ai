from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BEDROCK_DEFAULT_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

REPORT_SYSTEM_PROMPT = """당신은 AWS 솔루션 아키텍트입니다.
레포지토리 문맥과 추론된 아키텍처를 분석하세요.
반드시 한국어로만 작성하고, JSON만 반환하세요:
{
  "summary": string,
  "findings": string[],
  "recommendedStack": string[],
  "deploymentSteps": string[],
  "risks": string[],
  "costNotes": string[]
}
규칙:
- 각 리스트는 3~6개 이내로 간결하게 작성
- 반복되는 일반론 금지, 레포 특성에 맞는 내용 작성
- AWS 초보도 이해할 수 있게 쉬운 한국어로 설명
- 영문 문장/용어 남용 금지 (서비스명은 영어 표기 허용)
"""


def _extract_json_text(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("{") and trimmed.endswith("}"):
        return trimmed
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", trimmed, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1)
    start = trimmed.find("{")
    if start < 0:
        raise ValueError("no json object")
    depth = 0
    for idx in range(start, len(trimmed)):
        ch = trimmed[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return trimmed[start : idx + 1]
    raise ValueError("incomplete json object")


def _fallback_report(architecture: dict[str, Any]) -> dict[str, Any]:
    services = {str(s).lower() for s in architecture.get("additional_services", [])}
    ec2_count = int((architecture.get("ec2", {}) or {}).get("count", 1))
    rds_enabled = bool((architecture.get("rds", {}) or {}).get("enabled", False))

    if "s3" in services and "cloudfront" in services and ec2_count <= 1 and not rds_enabled:
        stack = ["Amazon S3", "Amazon CloudFront", "Amazon Route53"]
    elif "eks" in services:
        stack = ["Amazon EKS", "Amazon ECR", "Application Load Balancer"]
    elif "ecs" in services:
        stack = ["Amazon ECS (Fargate)", "Amazon ECR", "Application Load Balancer"]
    elif "lambda" in services:
        stack = ["AWS Lambda", "Amazon API Gateway", "Amazon CloudWatch"]
    else:
        stack = ["Amazon EC2", "Application Load Balancer"]

    findings = [
        f"현재 추정 구성은 EC2 {ec2_count}대로 시작하는 형태입니다.",
        "리포지토리 파일 신호를 AI가 읽어 배포 구성을 추정했습니다.",
    ]
    if rds_enabled:
        findings.append("데이터 저장소 필요 신호가 있어 RDS가 포함되었습니다.")

    steps = [
        "먼저 테스트/빌드가 통과되는 최소 배포 파이프라인을 연결합니다.",
        "환경 변수와 비밀값은 AWS Secrets Manager/SSM으로 분리합니다.",
        "배포 후 CloudWatch 로그와 알람을 붙여 오류를 빠르게 감지합니다.",
    ]
    risks = [
        "트래픽 예상치가 실제와 다르면 인스턴스 크기/비용이 달라질 수 있습니다.",
        "DB 사용 시 백업/복구 정책을 초기에 정하지 않으면 운영 위험이 커집니다.",
    ]
    cost_notes = [
        "초기에는 작은 인스턴스로 시작하고, 모니터링 후 단계적으로 확장하는 것이 안전합니다.",
    ]
    return {
        "summary": f"AI 분석 기준 기본 배포 타깃은 {stack[0]} 입니다.",
        "findings": findings,
        "recommendedStack": stack,
        "deploymentSteps": steps,
        "risks": risks,
        "costNotes": cost_notes,
    }


def _invoke_bedrock_report(prompt: str) -> str:
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1200,
        "temperature": 0.1,
        "system": REPORT_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(response["body"].read())
    texts = [block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"]
    return "\n".join(t for t in texts if t)


def generate_repo_report_with_ai(
    *,
    repo_prompt: str,
    architecture: dict[str, Any],
    model_rationale: dict[str, Any] | None = None,
    consistency_feedback: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    use_bedrock = os.getenv("BEDROCK_ENABLED", "true").lower() == "true"
    fallback_enabled = os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"
    strict_mode = os.getenv("BEDROCK_STRICT_MODE", "false").lower() == "true"

    feedback_text = ""
    if consistency_feedback:
        feedback_text = "\n\nConsistency feedback (must fix in output):\n" + "\n".join(
            f"- {line}" for line in consistency_feedback if line.strip()
        )

    prompt = (
        f"Repository context:\n{repo_prompt}\n\n"
        f"Inferred architecture JSON:\n{json.dumps(architecture, ensure_ascii=False)}\n\n"
        f"Model rationale:\n{json.dumps(model_rationale or {}, ensure_ascii=False)}"
        f"{feedback_text}"
    )

    if not use_bedrock:
        if strict_mode:
            raise RuntimeError("BEDROCK_ENABLED must be true in strict mode")
        return _fallback_report(architecture), {
            "provider": "local_fallback",
            "fallbackUsed": True,
            "reason": "bedrock_disabled",
        }

    try:
        raw = _invoke_bedrock_report(prompt)
        parsed = json.loads(_extract_json_text(raw))
        if not isinstance(parsed, dict):
            raise ValueError("report must be object")
        report = {
            "summary": str(parsed.get("summary", "")).strip(),
            "findings": [str(v).strip() for v in parsed.get("findings", []) if str(v).strip()],
            "recommendedStack": [str(v).strip() for v in parsed.get("recommendedStack", []) if str(v).strip()],
            "deploymentSteps": [str(v).strip() for v in parsed.get("deploymentSteps", []) if str(v).strip()],
            "risks": [str(v).strip() for v in parsed.get("risks", []) if str(v).strip()],
            "costNotes": [str(v).strip() for v in parsed.get("costNotes", []) if str(v).strip()],
        }
        if not report["summary"] or not report["recommendedStack"]:
            raise ValueError("missing essential report fields")
        return report, {
            "provider": "bedrock",
            "fallbackUsed": False,
            "reason": None,
        }
    except (ValueError, json.JSONDecodeError, ClientError, BotoCoreError):
        if fallback_enabled and not strict_mode:
            return _fallback_report(architecture), {
                "provider": "local_fallback",
                "fallbackUsed": True,
                "reason": "bedrock_invoke_or_parse_error",
            }
        raise
