from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from jsonschema import ValidationError, validate


class AIParseError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


SYSTEM_PROMPT = """You are an AWS architecture parser for an MVP project.
Return JSON only with this exact shape:
{
  "vpc": boolean,
  "ec2": { "count": integer, "instance_type": "t3.micro"|"t3.small"|"t3.medium" },
  "rds": { "enabled": boolean, "engine": "mysql"|"postgres"|null },
  "public": boolean,
  "region": "ap-northeast-2"|"ap-northeast-1"|"ap-southeast-1"|"us-east-1"|"us-east-2"
}
Defaults when unclear:
vpc=true, ec2.count=1, ec2.instance_type=t3.micro, rds.enabled=false, rds.engine=null, public=false, region=ap-northeast-2.
No extra keys.
"""

RETRY_PROMPT = """Your previous output was invalid.
Return only a valid JSON object that strictly matches the required schema.
No prose, no markdown, no extra keys.
"""


REGION_KEYWORDS = {
    "ap-northeast-2": ["서울", "seoul", "ap-northeast-2"],
    "ap-northeast-1": ["도쿄", "tokyo", "ap-northeast-1"],
    "ap-southeast-1": ["싱가포르", "singapore", "ap-southeast-1"],
    "us-east-1": ["버지니아", "virginia", "n. virginia", "us-east-1"],
    "us-east-2": ["오하이오", "ohio", "us-east-2"],
}


def _extract_json_text(text: str) -> str:
    trimmed = text.strip()
    fence = re.search(r"```json\s*(\{.*?\})\s*```", trimmed, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1)
    if trimmed.startswith("{") and trimmed.endswith("}"):
        return trimmed

    start = trimmed.find("{")
    if start == -1:
        raise AIParseError("PARSE_ERROR", "no JSON object found in model output")

    depth = 0
    for idx in range(start, len(trimmed)):
        ch = trimmed[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return trimmed[start : idx + 1]
    raise AIParseError("PARSE_ERROR", "incomplete JSON object in model output")


def _parse_count(text: str) -> int:
    lowered = text.lower()
    patterns = [
        r"(?:ec2|서버)\D{0,6}(\d+)\s*(?:개|대)?",
        r"(\d+)\s*(?:개|대)\s*(?:ec2|서버)",
        r"(?:ec2|서버)\s*x\s*(\d+)",
        r"(\d+)\s*(?:개|대)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, lowered)
        if matched:
            return max(1, min(10, int(matched.group(1))))
    if "여러 대" in text or "여러개" in text or "여러 개" in text:
        return 2
    if "두 대" in text or "둘" in text:
        return 2
    return 1


def _local_fallback_parse(input_text: str) -> dict[str, Any]:
    lowered = input_text.lower()
    region = "ap-northeast-2"
    for r, keys in REGION_KEYWORDS.items():
        if any(k in lowered for k in keys):
            region = r
            break

    instance_type = "t3.medium" if "t3.medium" in lowered else "t3.small" if "t3.small" in lowered else "t3.micro"
    uncertainty_signals = ["모르겠", "할지", "미정", "고민"]
    private_signals = ["비공개", "private", "내부망", "공개 안"]
    public_signals = ["퍼블릭", "인터넷", "public", "공개"]
    if any(k in lowered for k in private_signals):
        public = False
    elif any(k in lowered for k in uncertainty_signals) and any(k in lowered for k in public_signals):
        public = False
    else:
        public = any(k in lowered for k in public_signals)

    if any(k in lowered for k in ["db 없음", "rds 없음", "db 필요 없음", "rds 빼"]):
        rds = {"enabled": False, "engine": None}
    elif "mysql" in lowered:
        rds = {"enabled": True, "engine": "mysql"}
    elif "postgres" in lowered or "postgresql" in lowered:
        rds = {"enabled": True, "engine": "postgres"}
    else:
        rds = {"enabled": False, "engine": None}

    return {
        "vpc": True,
        "ec2": {"count": _parse_count(input_text), "instance_type": instance_type},
        "rds": rds,
        "public": bool(public),
        "region": region,
    }


def _invoke_bedrock(user_input: str, retry: bool = False) -> str:
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
    user_prompt = f"{RETRY_PROMPT if retry else ''}\nRequirement:\n{user_input}"

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 700,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
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


def parse_architecture_with_retry(input_text: str, schema: dict[str, Any]) -> dict[str, Any]:
    use_bedrock = os.getenv("BEDROCK_ENABLED", "true").lower() == "true"
    fallback_enabled = os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"
    last_error: AIParseError | None = None

    for attempt in range(2):
        try:
            if use_bedrock:
                raw_text = _invoke_bedrock(input_text, retry=(attempt == 1))
                parsed = json.loads(_extract_json_text(raw_text))
            else:
                parsed = _local_fallback_parse(input_text)

            validate(instance=parsed, schema=schema)
            return parsed
        except ValidationError as e:
            last_error = AIParseError("SCHEMA_ERROR", e.message)
        except json.JSONDecodeError as e:
            last_error = AIParseError("PARSE_ERROR", str(e))
        except AIParseError as e:
            last_error = e
        except (ClientError, BotoCoreError) as e:
            if fallback_enabled:
                parsed = _local_fallback_parse(input_text)
                validate(instance=parsed, schema=schema)
                return parsed
            last_error = AIParseError("INTERNAL_ERROR", str(e))
        except Exception as e:  # noqa: BLE001
            last_error = AIParseError("INTERNAL_ERROR", str(e))

    if last_error is None:
        raise AIParseError("INTERNAL_ERROR", "unknown parse failure")
    raise last_error
