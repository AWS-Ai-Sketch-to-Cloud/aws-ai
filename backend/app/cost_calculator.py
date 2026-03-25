from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


EC2_BASE_MONTHLY_KRW = {
    "t3.micro": 12000,
    "t3.small": 22000,
    "t3.medium": 43000,
}

RDS_BASE_MONTHLY_KRW = {
    "mysql": 18000,
    "postgres": 20000,
}

REGION_FACTOR = {
    "ap-northeast-2": 1.00,
    "ap-northeast-1": 1.08,
    "ap-southeast-1": 1.03,
    "us-east-1": 0.94,
    "us-east-2": 0.91,
}

AWS_LOCATION_BY_REGION = {
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
}

USD_TO_KRW_DEFAULT = float(os.getenv("USD_TO_KRW", "1350"))
HOURS_PER_MONTH_DEFAULT = int(os.getenv("COST_HOURS_PER_MONTH", "730"))
PRICING_REGION = os.getenv("AWS_PRICING_REGION", "us-east-1")
BEDROCK_INPUT_TOKENS_MONTHLY = int(os.getenv("BEDROCK_INPUT_TOKENS_MONTHLY", "2000000"))
BEDROCK_OUTPUT_TOKENS_MONTHLY = int(os.getenv("BEDROCK_OUTPUT_TOKENS_MONTHLY", "500000"))

# Approximate on-demand token pricing for Claude 3 Haiku (USD per 1K tokens).
BEDROCK_TOKEN_PRICING_USD_PER_1K = {
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
    "apac.anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
}

ADDITIONAL_SERVICE_MONTHLY_KRW = {
    "s3": 5000,
    "alb": 25000,
    "cloudfront": 12000,
    "lambda": 8000,
    "apigateway": 7000,
    "dynamodb": 15000,
    "elasticache": 30000,
    "sqs": 3000,
    "sns": 2000,
    "ecs": 35000,
    "eks": 120000,
    "nat-gateway": 45000,
    "vpc-endpoint": 18000,
}


@lru_cache(maxsize=1)
def _pricing_client():
    return boto3.client("pricing", region_name=PRICING_REGION)


def _extract_usd_hourly_from_price_list(price_list: list[str]) -> float | None:
    candidates: list[float] = []
    for raw in price_list:
        item = json.loads(raw)
        terms = item.get("terms", {}).get("OnDemand", {})
        for term in terms.values():
            dims = term.get("priceDimensions", {})
            for dim in dims.values():
                usd_text = dim.get("pricePerUnit", {}).get("USD")
                if not usd_text:
                    continue
                try:
                    usd = float(usd_text)
                except ValueError:
                    continue
                if usd > 0:
                    candidates.append(usd)
    return min(candidates) if candidates else None


def _query_ec2_hourly_usd(instance_type: str, location: str) -> float | None:
    client = _pricing_client()
    response = client.get_products(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ],
        MaxResults=100,
    )
    return _extract_usd_hourly_from_price_list(response.get("PriceList", []))


def _query_rds_hourly_usd(engine: str, location: str) -> float | None:
    db_engine = "MySQL" if engine == "mysql" else "PostgreSQL"
    client = _pricing_client()
    response = client.get_products(
        ServiceCode="AmazonRDS",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t3.micro"},
            {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": db_engine},
            {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
        ],
        MaxResults=100,
    )
    return _extract_usd_hourly_from_price_list(response.get("PriceList", []))


def _estimate_with_pricing_api(
    instance_type: str,
    ec2_count: int,
    rds_enabled: bool,
    rds_engine: str | None,
    region: str,
) -> tuple[int, int, dict[str, Any]]:
    location = AWS_LOCATION_BY_REGION.get(region)
    if not location:
        raise ValueError(f"unsupported pricing region: {region}")

    hours = HOURS_PER_MONTH_DEFAULT
    usd_to_krw = USD_TO_KRW_DEFAULT

    ec2_hourly_usd = _query_ec2_hourly_usd(instance_type, location)
    if ec2_hourly_usd is None:
        raise ValueError(f"ec2 hourly pricing not found for {instance_type} in {location}")

    ec2_cost = round(ec2_hourly_usd * hours * usd_to_krw * ec2_count)

    rds_cost = 0
    rds_hourly_usd = None
    if rds_enabled:
        if rds_engine not in {"mysql", "postgres"}:
            raise ValueError(f"unsupported rds engine: {rds_engine}")
        rds_hourly_usd = _query_rds_hourly_usd(rds_engine, location)
        if rds_hourly_usd is None:
            raise ValueError(f"rds hourly pricing not found for {rds_engine} in {location}")
        rds_cost = round(rds_hourly_usd * hours * usd_to_krw)

    assumptions = {
        "pricing_source": "aws_pricing_api",
        "pricing_region_endpoint": PRICING_REGION,
        "aws_location": location,
        "hours_per_month": hours,
        "usd_to_krw": usd_to_krw,
        "ec2_hourly_usd": ec2_hourly_usd,
        "rds_hourly_usd": rds_hourly_usd if rds_enabled else 0,
        "rds_instance_type": "db.t3.micro" if rds_enabled else None,
    }
    return ec2_cost, rds_cost, assumptions


def estimate_monthly_cost(architecture: dict[str, Any]) -> dict[str, Any]:
    ec2 = architecture.get("ec2", {})
    rds = architecture.get("rds", {})
    bedrock = architecture.get("bedrock", {})
    additional_services = [str(s).lower() for s in architecture.get("additional_services", []) if str(s).strip()]
    region = architecture.get("region", "ap-northeast-2")

    instance_type = ec2.get("instance_type", "t3.micro")
    ec2_count = int(ec2.get("count", 1))
    rds_enabled = bool(rds.get("enabled", False))
    rds_engine = rds.get("engine")
    bedrock_enabled = bool(bedrock.get("enabled", False))
    bedrock_model = bedrock.get("model") or "anthropic.claude-3-haiku-20240307-v1:0"
    pricing_error = None
    try:
        ec2_cost, rds_cost, pricing_assumptions = _estimate_with_pricing_api(
            instance_type=instance_type,
            ec2_count=ec2_count,
            rds_enabled=rds_enabled,
            rds_engine=rds_engine,
            region=region,
        )
    except (ClientError, BotoCoreError, ValueError) as e:
        pricing_error = str(e)
        region_factor = REGION_FACTOR.get(region, 1.00)
        ec2_unit_base = EC2_BASE_MONTHLY_KRW.get(instance_type, EC2_BASE_MONTHLY_KRW["t3.micro"])
        ec2_unit = round(ec2_unit_base * region_factor)
        ec2_cost = ec2_unit * ec2_count

        rds_cost = 0
        if rds_enabled:
            rds_unit_base = RDS_BASE_MONTHLY_KRW.get(rds_engine, RDS_BASE_MONTHLY_KRW["mysql"])
            rds_cost = round(rds_unit_base * region_factor)
        pricing_assumptions = {
            "pricing_source": "fallback_static_table",
            "region_factor": region_factor,
            "ec2_unit_krw": ec2_unit,
            "rds_unit_krw": rds_cost if rds_enabled else 0,
            "pricing_error": pricing_error,
        }

    bedrock_cost = 0
    if bedrock_enabled:
        model_pricing = BEDROCK_TOKEN_PRICING_USD_PER_1K.get(bedrock_model)
        if model_pricing:
            usd_to_krw = float(pricing_assumptions.get("usd_to_krw", USD_TO_KRW_DEFAULT))
            bedrock_input_cost_usd = (BEDROCK_INPUT_TOKENS_MONTHLY / 1000.0) * model_pricing["input"]
            bedrock_output_cost_usd = (BEDROCK_OUTPUT_TOKENS_MONTHLY / 1000.0) * model_pricing["output"]
            bedrock_cost = round((bedrock_input_cost_usd + bedrock_output_cost_usd) * usd_to_krw)
        else:
            bedrock_cost = 0

    additional_service_costs: dict[str, int] = {}
    for service in sorted(set(additional_services)):
        if service in {"ec2", "rds", "bedrock", "total"}:
            continue
        additional_service_costs[service] = int(ADDITIONAL_SERVICE_MONTHLY_KRW.get(service, 0))

    additional_services_total = sum(additional_service_costs.values())

    total = ec2_cost + rds_cost + bedrock_cost + additional_services_total
    assumptions = {
        "currency": "KRW",
        "region": region,
        "ec2_type": instance_type,
        "ec2_count": ec2_count,
        "rds_enabled": rds_enabled,
        "rds_engine": rds_engine,
        "bedrock_enabled": bedrock_enabled,
        "bedrock_model": bedrock_model if bedrock_enabled else None,
        "bedrock_input_tokens_monthly": BEDROCK_INPUT_TOKENS_MONTHLY if bedrock_enabled else 0,
        "bedrock_output_tokens_monthly": BEDROCK_OUTPUT_TOKENS_MONTHLY if bedrock_enabled else 0,
        "additional_services": sorted(set(additional_services)),
        "additional_service_assumptions": additional_service_costs,
        "pricing_version": "v3-live-pricing",
        **pricing_assumptions,
    }
    breakdown = {
        "ec2": ec2_cost,
        "rds": rds_cost,
        "bedrock": bedrock_cost,
        **additional_service_costs,
        "total": total,
    }
    return {
        "currency": "KRW",
        "region": region,
        "assumptions": assumptions,
        "monthly_total": total,
        "breakdown": breakdown,
    }

