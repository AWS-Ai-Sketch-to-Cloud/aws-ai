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


SYSTEM_PROMPT = """You are an AWS architecture parser.
Return JSON only with this exact shape:
{
  "vpc": boolean,
  "ec2": { "count": integer, "instance_type": "t3.micro"|"t3.small"|"t3.medium" },
  "rds": { "enabled": boolean, "engine": "mysql"|"postgres"|null },
  "bedrock": { "enabled": boolean, "model": "anthropic.claude-3-haiku-20240307-v1:0"|"apac.anthropic.claude-3-haiku-20240307-v1:0"|null },
  "additional_services": string[],
  "public": boolean,
  "region": "ap-northeast-2"|"ap-northeast-1"|"ap-southeast-1"|"us-east-1"|"us-east-2"
}
Defaults when unclear:
vpc=true, ec2.count=1, ec2.instance_type=t3.micro, rds.enabled=false, rds.engine=null, bedrock.enabled=false, bedrock.model=null, additional_services=[], public=false, region=ap-northeast-2.
No extra keys.
When image is provided, infer from icons, labels, and connection patterns.
"""

RETRY_PROMPT = """Your previous output was invalid.
Return only a valid JSON object that strictly matches the required schema.
No prose, no markdown, no extra keys.
"""

BEDROCK_DEFAULT_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

REGION_KEYWORDS = {
    "ap-northeast-2": ["seoul", "korea", "ap-northeast-2"],
    "ap-northeast-1": ["tokyo", "japan", "ap-northeast-1"],
    "ap-southeast-1": ["singapore", "ap-southeast-1"],
    "us-east-1": ["virginia", "n. virginia", "us-east-1"],
    "us-east-2": ["ohio", "us-east-2"],
}

SERVICE_KEYWORDS: dict[str, list[str]] = {
    "s3": ["s3", "bucket", "object storage"],
    "alb": ["alb", "load balancer", "application load balancer"],
    "cloudfront": ["cloudfront", "cdn"],
    "lambda": ["lambda", "serverless function"],
    "apigateway": ["api gateway", "apigateway"],
    "dynamodb": ["dynamodb"],
    "elasticache": ["elasticache", "redis", "memcached"],
    "sqs": ["sqs", "queue"],
    "sns": ["sns", "topic", "notification"],
    "ecs": ["ecs", "fargate"],
    "eks": ["eks", "kubernetes"],
    "nat-gateway": ["nat gateway", "natgw"],
    "vpc-endpoint": ["vpc endpoint", "private endpoint"],
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
        r"(?:ec2|server|instance)\D{0,8}(\d+)",
        r"(\d+)\D{0,8}(?:ec2|server|instance)",
        r"(?:ec2|server|instance)\s*x\s*(\d+)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, lowered)
        if matched:
            return max(1, min(10, int(matched.group(1))))
    if any(k in lowered for k in ["multiple", "several", "redundant", "high availability", "ha"]):
        return 2
    return 1


def _extract_services_from_text(lowered: str) -> list[str]:
    services: list[str] = []
    for service, keys in SERVICE_KEYWORDS.items():
        if any(k in lowered for k in keys):
            services.append(service)
    return sorted(set(services))


def _local_fallback_parse(input_text: str) -> dict[str, Any]:
    lowered = input_text.lower()
    region = "ap-northeast-2"
    for candidate, keys in REGION_KEYWORDS.items():
        if any(k in lowered for k in keys):
            region = candidate
            break

    if "t3.medium" in lowered:
        instance_type = "t3.medium"
    elif "t3.small" in lowered:
        instance_type = "t3.small"
    else:
        instance_type = "t3.micro"

    public = any(k in lowered for k in ["public", "internet", "external"]) and not any(
        k in lowered for k in ["private", "internal only", "non-public"]
    )

    if any(k in lowered for k in ["no db", "without db", "without rds"]):
        rds = {"enabled": False, "engine": None}
    elif "postgres" in lowered or "postgresql" in lowered:
        rds = {"enabled": True, "engine": "postgres"}
    elif any(k in lowered for k in ["rds", "database", "mysql"]):
        rds = {"enabled": True, "engine": "mysql"}
    else:
        rds = {"enabled": False, "engine": None}

    bedrock_enabled = any(k in lowered for k in ["bedrock", "claude", "anthropic", "generative ai", "llm", " ai "])
    bedrock = {"enabled": bedrock_enabled, "model": BEDROCK_DEFAULT_MODEL if bedrock_enabled else None}

    additional_services = _extract_services_from_text(lowered)
    if bedrock_enabled and "bedrock" not in additional_services:
        additional_services.append("bedrock")
    if rds["enabled"] and "rds" not in additional_services:
        additional_services.append("rds")

    return {
        "vpc": True,
        "ec2": {"count": _parse_count(input_text), "instance_type": instance_type},
        "rds": rds,
        "bedrock": bedrock,
        "additional_services": sorted(set(additional_services)),
        "public": bool(public),
        "region": region,
    }


def _invoke_bedrock(user_input: str, retry: bool = False) -> str:
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL)
    user_prompt = f"{RETRY_PROMPT if retry else ''}\nRequirement:\n{user_input}"

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
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


def _extract_image_from_data_url(data_url: str) -> tuple[str, str]:
    matched = re.match(r"^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$", data_url, re.DOTALL)
    if not matched:
        raise AIParseError("PARSE_ERROR", "invalid image data url format")
    media_type = matched.group(1).lower()
    base64_data = matched.group(2).strip()
    if not base64_data:
        raise AIParseError("PARSE_ERROR", "empty image payload")
    return media_type, base64_data


def _invoke_bedrock_with_image(user_input: str, image_data_url: str, retry: bool = False) -> str:
    region = os.getenv("AWS_REGION", "ap-northeast-2")
    model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL)
    user_prompt = f"{RETRY_PROMPT if retry else ''}\nRequirement:\n{user_input}"
    media_type, image_base64 = _extract_image_from_data_url(image_data_url)
    if media_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        raise AIParseError("PARSE_ERROR", "unsupported image media type")

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1400,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                    },
                ],
            }
        ],
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


def _normalize_architecture(parsed: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(parsed)
    if "bedrock" not in normalized or not isinstance(normalized.get("bedrock"), dict):
        normalized["bedrock"] = {"enabled": False, "model": None}
    else:
        enabled = bool(normalized["bedrock"].get("enabled", False))
        normalized["bedrock"] = {"enabled": enabled, "model": normalized["bedrock"].get("model") if enabled else None}

    if "ec2" not in normalized or not isinstance(normalized.get("ec2"), dict):
        normalized["ec2"] = {"count": 1, "instance_type": "t3.micro"}
    if "rds" not in normalized or not isinstance(normalized.get("rds"), dict):
        normalized["rds"] = {"enabled": False, "engine": None}

    services = normalized.get("additional_services")
    if not isinstance(services, list):
        services = []
    service_list = [str(s).strip().lower() for s in services if str(s).strip()]
    if normalized["bedrock"]["enabled"]:
        service_list.append("bedrock")
    if normalized["rds"].get("enabled"):
        service_list.append("rds")
    normalized["additional_services"] = sorted(set(service_list))
    return normalized


def _apply_requirement_hints(input_text: str, parsed: dict[str, Any]) -> dict[str, Any]:
    lowered = input_text.lower()
    normalized = dict(parsed)

    ec2_obj = normalized.get("ec2", {"count": 1, "instance_type": "t3.micro"})
    ec2_count = _parse_count(input_text)
    ec2_obj["count"] = ec2_count
    normalized["ec2"] = ec2_obj

    if any(k in lowered for k in ["rds", "database", " db ", "mysql", "postgres", "postgresql"]):
        if "postgres" in lowered or "postgresql" in lowered:
            normalized["rds"] = {"enabled": True, "engine": "postgres"}
        else:
            normalized["rds"] = {"enabled": True, "engine": "mysql"}

    bedrock_hint = any(k in lowered for k in ["bedrock", "claude", "anthropic", "generative ai", "llm", " ai "])
    if bedrock_hint:
        normalized["bedrock"] = {"enabled": True, "model": BEDROCK_DEFAULT_MODEL}

    services = [str(s).lower() for s in normalized.get("additional_services", []) if str(s).strip()]
    services.extend(_extract_services_from_text(lowered))
    if normalized.get("bedrock", {}).get("enabled"):
        services.append("bedrock")
    if normalized.get("rds", {}).get("enabled"):
        services.append("rds")
    normalized["additional_services"] = sorted(set(services))
    return normalized


def parse_architecture_with_retry(
    input_text: str, schema: dict[str, Any], input_image_data_url: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    use_bedrock = os.getenv("BEDROCK_ENABLED", "true").lower() == "true"
    fallback_enabled = os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"
    model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL)
    used_image = bool(input_image_data_url)
    last_error: AIParseError | None = None

    for attempt in range(2):
        try:
            if use_bedrock:
                raw_text = (
                    _invoke_bedrock_with_image(input_text, input_image_data_url, retry=(attempt == 1))
                    if input_image_data_url
                    else _invoke_bedrock(input_text, retry=(attempt == 1))
                )
                parsed = _apply_requirement_hints(input_text, _normalize_architecture(json.loads(_extract_json_text(raw_text))))
                meta = {"provider": "bedrock", "modelId": model_id, "usedImage": used_image, "fallbackUsed": False}
            else:
                parsed = _apply_requirement_hints(input_text, _normalize_architecture(_local_fallback_parse(input_text)))
                meta = {"provider": "local_fallback", "modelId": None, "usedImage": used_image, "fallbackUsed": True}

            validate(instance=parsed, schema=schema)
            return parsed, meta
        except ValidationError as e:
            last_error = AIParseError("SCHEMA_ERROR", e.message)
        except json.JSONDecodeError as e:
            last_error = AIParseError("PARSE_ERROR", str(e))
        except AIParseError as e:
            last_error = e
        except (ClientError, BotoCoreError) as e:
            if fallback_enabled:
                parsed = _apply_requirement_hints(input_text, _normalize_architecture(_local_fallback_parse(input_text)))
                validate(instance=parsed, schema=schema)
                return parsed, {"provider": "local_fallback", "modelId": model_id, "usedImage": used_image, "fallbackUsed": True}
            last_error = AIParseError("INTERNAL_ERROR", str(e))
        except Exception as e:  # noqa: BLE001
            last_error = AIParseError("INTERNAL_ERROR", str(e))

    if last_error is None:
        raise AIParseError("INTERNAL_ERROR", "unknown parse failure")
    raise last_error
