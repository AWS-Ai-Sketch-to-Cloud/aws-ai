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
  "ec2": { "count": integer, "instance_type": "t3.nano"|"t3.micro"|"t3.small"|"t3.medium"|"t3.large"|"m6i.large"|"m6i.xlarge"|"c6i.large"|"c6i.xlarge"|"r6i.large"|"r6i.xlarge" },
  "rds": { "enabled": boolean, "engine": "mysql"|"postgres"|null },
  "bedrock": { "enabled": boolean, "model": "anthropic.claude-3-haiku-20240307-v1:0"|"apac.anthropic.claude-3-haiku-20240307-v1:0"|null },
  "additional_services": string[],
  "usage": { "monthly_hours": integer, "data_transfer_gb": number, "storage_gb": number, "requests_million": number },
  "public": boolean,
  "region": "ap-northeast-2"|"ap-northeast-1"|"ap-southeast-1"|"us-east-1"|"us-east-2"
}
Defaults when unclear:
vpc=true, ec2.count=1, ec2.instance_type=t3.micro, rds.enabled=false, rds.engine=null, bedrock.enabled=false, bedrock.model=null, additional_services=[], usage.monthly_hours=730, usage.data_transfer_gb=100, usage.storage_gb=50, usage.requests_million=5, public=false, region=ap-northeast-2.
No extra keys.
When image is provided, infer from icons, labels, and connection patterns.
"""

RETRY_PROMPT = """Your previous output was invalid.
Return only a valid JSON object that strictly matches the required schema.
No prose, no markdown, no extra keys.
"""

BEDROCK_DEFAULT_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
DEFAULT_USAGE = {
    "monthly_hours": 730,
    "data_transfer_gb": 100.0,
    "storage_gb": 50.0,
    "requests_million": 5.0,
}

INSTANCE_TYPE_KEYWORDS = [
    "t3.nano",
    "t3.micro",
    "t3.small",
    "t3.medium",
    "t3.large",
    "m6i.large",
    "m6i.xlarge",
    "c6i.large",
    "c6i.xlarge",
    "r6i.large",
    "r6i.xlarge",
]

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
    "autoscaling": ["autoscaling", "auto scaling", "asg"],
    "cloudwatch": ["cloudwatch", "monitoring", "alarm"],
    "waf": ["waf", "web application firewall"],
    "route53": ["route53", "route 53", "dns"],
    "efs": ["efs", "elastic file system", "shared file system"],
    "eventbridge": ["eventbridge", "event bus"],
    "stepfunctions": ["step functions", "stepfunctions", "state machine"],
    "kinesis": ["kinesis", "stream"],
    "opensearch": ["opensearch", "elasticsearch"],
    "athena": ["athena"],
    "redshift": ["redshift", "data warehouse"],
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


def _parse_count_hint(text: str) -> int | None:
    lowered = text.lower()
    patterns = [
        r"(?:ec2|server|instance)\D{0,8}(\d+)",
        r"(\d+)\D{0,8}(?:ec2|server|instance)",
        r"(?:ec2|server|instance)\s*x\s*(\d+)",
        r"(\d+)\s*(?:대|개)\s*(?:ec2|server|instance)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, lowered)
        if matched:
            return max(1, min(10, int(matched.group(1))))
    if any(k in lowered for k in ["multiple", "several", "redundant", "high availability", "ha"]):
        return 2
    return None


def _parse_count(text: str) -> int:
    return _parse_count_hint(text) or 1


def _find_instance_type_hint(text: str) -> str | None:
    lowered = text.lower()
    for instance_type in INSTANCE_TYPE_KEYWORDS:
        if instance_type in lowered:
            return instance_type
    return None


def _parse_instance_type(text: str) -> str:
    return _find_instance_type_hint(text) or "t3.micro"


def _extract_first_number(pattern: str, text: str) -> float | None:
    matched = re.search(pattern, text, re.IGNORECASE)
    if not matched:
        return None
    try:
        return float(matched.group(1))
    except (TypeError, ValueError):
        return None


def _extract_number_after_keywords(text: str, keywords: list[str], unit_pattern: str) -> float | None:
    keyword_union = "|".join(re.escape(k) for k in keywords)
    pattern = rf"(?:{keyword_union})[^0-9]{{0,20}}(\d+(?:\.\d+)?)\s*{unit_pattern}"
    return _extract_first_number(pattern, text)


def _parse_usage_hints(text: str, *, apply_defaults: bool = True) -> dict[str, float | int]:
    lowered = text.lower()
    usage: dict[str, float | int] = dict(DEFAULT_USAGE) if apply_defaults else {}

    hours = _extract_first_number(r"(?:hours|hour|시간)[^\d]{0,8}(\d+(?:\.\d+)?)", lowered)
    if hours is not None:
        usage["monthly_hours"] = max(1, min(744, int(round(hours))))

    has_transfer_keyword = any(k in lowered for k in ["data transfer", "egress", "트래픽", "전송량"])
    if has_transfer_keyword:
        data_transfer_tb = _extract_number_after_keywords(
            lowered, ["data transfer", "egress", "트래픽", "전송량"], r"tb"
        )
        if data_transfer_tb is not None:
            usage["data_transfer_gb"] = max(0.0, data_transfer_tb * 1024)
        else:
            data_transfer_gb = _extract_number_after_keywords(
                lowered, ["data transfer", "egress", "트래픽", "전송량"], r"gb"
            )
            if data_transfer_gb is not None:
                usage["data_transfer_gb"] = max(0.0, data_transfer_gb)

    has_storage_keyword = any(k in lowered for k in ["storage", "저장", "s3"])
    if has_storage_keyword:
        storage_tb = _extract_number_after_keywords(lowered, ["storage", "저장", "s3"], r"tb")
        if storage_tb is not None:
            usage["storage_gb"] = max(0.0, storage_tb * 1024)
        else:
            storage_gb = _extract_number_after_keywords(lowered, ["storage", "저장", "s3"], r"gb")
            if storage_gb is not None:
                usage["storage_gb"] = max(0.0, storage_gb)

    has_request_keyword = any(k in lowered for k in ["request", "요청", "호출"])
    if has_request_keyword:
        requests_million = _extract_number_after_keywords(lowered, ["request", "요청", "호출"], r"(?:m|million|백만)")
        if requests_million is not None:
            usage["requests_million"] = max(0.0, requests_million)
        else:
            requests_raw = _extract_number_after_keywords(lowered, ["request", "요청", "호출"], r"(?:req|requests?)")
            if requests_raw is not None:
                usage["requests_million"] = max(0.0, requests_raw / 1_000_000)

    return usage


def _extract_services_from_text(lowered: str) -> list[str]:
    services: list[str] = []
    for service, keys in SERVICE_KEYWORDS.items():
        if any(k in lowered for k in keys):
            services.append(service)
    return sorted(set(services))


def _build_requirement_coverage_meta(input_text: str, parsed: dict[str, Any]) -> dict[str, Any]:
    lowered = input_text.lower()
    checks: list[tuple[str, bool]] = []

    ec2_count_hint = _parse_count_hint(input_text)
    if ec2_count_hint is not None:
        parsed_count = int((parsed.get("ec2", {}) or {}).get("count", 1))
        checks.append(("ec2_count", parsed_count == ec2_count_hint))

    ec2_type_hint = _find_instance_type_hint(input_text)
    if ec2_type_hint:
        parsed_type = str((parsed.get("ec2", {}) or {}).get("instance_type", "t3.micro"))
        checks.append(("ec2_instance_type", parsed_type == ec2_type_hint))

    region_hint = None
    for candidate, keys in REGION_KEYWORDS.items():
        if any(k in lowered for k in keys):
            region_hint = candidate
            break
    if region_hint:
        checks.append(("region", parsed.get("region") == region_hint))

    wants_rds = any(k in lowered for k in ["rds", "database", " db ", "mysql", "postgres", "postgresql"])
    if wants_rds:
        checks.append(("rds", bool((parsed.get("rds", {}) or {}).get("enabled"))))

    wants_bedrock = any(k in lowered for k in ["bedrock", "claude", "anthropic", "generative ai", "llm", " ai "])
    if wants_bedrock:
        checks.append(("bedrock", bool((parsed.get("bedrock", {}) or {}).get("enabled"))))

    expected_services = set(_extract_services_from_text(lowered))
    parsed_services = {
        str(s).lower()
        for s in parsed.get("additional_services", [])
        if str(s).strip()
    }
    for service in sorted(expected_services):
        checks.append((f"service:{service}", service in parsed_services))

    usage_hints = _parse_usage_hints(input_text, apply_defaults=False)
    parsed_usage = parsed.get("usage", {}) or {}
    for key, expected in usage_hints.items():
        try:
            actual = float(parsed_usage.get(key, -1))
            checks.append((f"usage:{key}", abs(actual - float(expected)) < 0.0001))
        except (TypeError, ValueError):
            checks.append((f"usage:{key}", False))

    if not checks:
        return {"requirementCoverage": 1.0, "unmetHints": []}

    unmet = [name for name, ok in checks if not ok]
    met_count = len(checks) - len(unmet)
    coverage = round(met_count / len(checks), 3)
    return {"requirementCoverage": coverage, "unmetHints": unmet}


def _local_fallback_parse(input_text: str) -> dict[str, Any]:
    lowered = input_text.lower()
    region = "ap-northeast-2"
    for candidate, keys in REGION_KEYWORDS.items():
        if any(k in lowered for k in keys):
            region = candidate
            break

    instance_type = _parse_instance_type(input_text)

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
        "usage": _parse_usage_hints(input_text),
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
    if "usage" not in normalized or not isinstance(normalized.get("usage"), dict):
        normalized["usage"] = dict(DEFAULT_USAGE)
    else:
        usage = normalized["usage"]

        def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
            try:
                return max(minimum, min(maximum, int(float(value))))
            except (TypeError, ValueError):
                return default

        def _safe_float(value: Any, default: float, minimum: float, maximum: float) -> float:
            try:
                return max(minimum, min(maximum, float(value)))
            except (TypeError, ValueError):
                return default

        normalized["usage"] = {
            "monthly_hours": _safe_int(usage.get("monthly_hours"), int(DEFAULT_USAGE["monthly_hours"]), 1, 744),
            "data_transfer_gb": _safe_float(usage.get("data_transfer_gb"), float(DEFAULT_USAGE["data_transfer_gb"]), 0.0, 100000.0),
            "storage_gb": _safe_float(usage.get("storage_gb"), float(DEFAULT_USAGE["storage_gb"]), 0.0, 100000.0),
            "requests_million": _safe_float(usage.get("requests_million"), float(DEFAULT_USAGE["requests_million"]), 0.0, 100000.0),
        }

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
    ec2_count_hint = _parse_count_hint(input_text)
    if ec2_count_hint is not None:
        ec2_obj["count"] = ec2_count_hint
    instance_type_hint = _find_instance_type_hint(input_text)
    if instance_type_hint:
        ec2_obj["instance_type"] = instance_type_hint
    normalized["ec2"] = ec2_obj

    for candidate, keys in REGION_KEYWORDS.items():
        if any(k in lowered for k in keys):
            normalized["region"] = candidate
            break

    usage_hints = _parse_usage_hints(input_text, apply_defaults=False)
    usage_current = dict(DEFAULT_USAGE)
    usage_current.update(normalized.get("usage", {}))
    usage_current.update(usage_hints)
    normalized["usage"] = usage_current

    if any(k in lowered for k in ["no db", "without db", "without rds", "db 제외", "rds 제외"]):
        normalized["rds"] = {"enabled": False, "engine": None}
    elif any(k in lowered for k in ["rds", "database", " db ", "mysql", "postgres", "postgresql"]):
        if "postgres" in lowered or "postgresql" in lowered:
            normalized["rds"] = {"enabled": True, "engine": "postgres"}
        else:
            normalized["rds"] = {"enabled": True, "engine": "mysql"}

    bedrock_hint = any(k in lowered for k in ["bedrock", "claude", "anthropic", "generative ai", "llm", " ai "])
    no_bedrock_hint = any(k in lowered for k in ["without bedrock", "no bedrock", "bedrock 제외"])
    if no_bedrock_hint:
        normalized["bedrock"] = {"enabled": False, "model": None}
    elif bedrock_hint:
        normalized["bedrock"] = {"enabled": True, "model": BEDROCK_DEFAULT_MODEL}

    if any(k in lowered for k in ["private", "internal only", "non-public", "비공개"]):
        normalized["public"] = False
    elif any(k in lowered for k in ["public", "internet", "external", "퍼블릭"]):
        normalized["public"] = True

    services = [str(s).lower() for s in normalized.get("additional_services", []) if str(s).strip()]
    services.extend(_extract_services_from_text(lowered))

    for service, keys in SERVICE_KEYWORDS.items():
        if any(f"without {k}" in lowered or f"no {k}" in lowered for k in keys):
            services = [s for s in services if s != service]
        if any(f"{k} 제외" in lowered for k in keys):
            services = [s for s in services if s != service]

    if normalized.get("bedrock", {}).get("enabled"):
        services.append("bedrock")
    else:
        services = [s for s in services if s != "bedrock"]
    if normalized.get("rds", {}).get("enabled"):
        services.append("rds")
    else:
        services = [s for s in services if s != "rds"]
    normalized["additional_services"] = sorted(set(services))
    return normalized


def parse_architecture_with_retry(
    input_text: str, schema: dict[str, Any], input_image_data_url: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    use_bedrock = os.getenv("BEDROCK_ENABLED", "true").lower() == "true"
    fallback_enabled = os.getenv("BEDROCK_FALLBACK_ENABLED", "true").lower() == "true"
    strict_mode = os.getenv("BEDROCK_STRICT_MODE", "false").lower() == "true"
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
                coverage_meta = _build_requirement_coverage_meta(input_text, parsed)
                meta = {
                    "provider": "bedrock",
                    "modelId": model_id,
                    "usedImage": used_image,
                    "fallbackUsed": False,
                    **coverage_meta,
                }
            else:
                parsed = _apply_requirement_hints(input_text, _normalize_architecture(_local_fallback_parse(input_text)))
                coverage_meta = _build_requirement_coverage_meta(input_text, parsed)
                meta = {
                    "provider": "local_fallback",
                    "modelId": None,
                    "usedImage": used_image,
                    "fallbackUsed": True,
                    **coverage_meta,
                }

            validate(instance=parsed, schema=schema)
            return parsed, meta
        except ValidationError as e:
            last_error = AIParseError("SCHEMA_ERROR", e.message)
        except json.JSONDecodeError as e:
            last_error = AIParseError("PARSE_ERROR", str(e))
        except AIParseError as e:
            last_error = e
        except (ClientError, BotoCoreError) as e:
            if fallback_enabled or not strict_mode:
                parsed = _apply_requirement_hints(input_text, _normalize_architecture(_local_fallback_parse(input_text)))
                validate(instance=parsed, schema=schema)
                coverage_meta = _build_requirement_coverage_meta(input_text, parsed)
                return parsed, {
                    "provider": "local_fallback",
                    "modelId": model_id,
                    "usedImage": used_image,
                    "fallbackUsed": True,
                    **coverage_meta,
                }
            last_error = AIParseError("INTERNAL_ERROR", str(e))
        except Exception as e:  # noqa: BLE001
            last_error = AIParseError("INTERNAL_ERROR", str(e))

    if last_error is None:
        raise AIParseError("INTERNAL_ERROR", "unknown parse failure")
    raise last_error
