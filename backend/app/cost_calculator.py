from __future__ import annotations

import json
import os
from copy import deepcopy
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


EC2_BASE_MONTHLY_KRW = {
    "t3.nano": 7000,
    "t3.micro": 12000,
    "t3.small": 22000,
    "t3.medium": 43000,
    "t3.large": 84000,
    "m6i.large": 98000,
    "m6i.xlarge": 196000,
    "c6i.large": 92000,
    "c6i.xlarge": 184000,
    "r6i.large": 112000,
    "r6i.xlarge": 224000,
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
OUTPUT_CURRENCY = os.getenv("COST_OUTPUT_CURRENCY", "USD").upper()
BEDROCK_INPUT_TOKENS_MONTHLY = int(os.getenv("BEDROCK_INPUT_TOKENS_MONTHLY", "2000000"))
BEDROCK_OUTPUT_TOKENS_MONTHLY = int(os.getenv("BEDROCK_OUTPUT_TOKENS_MONTHLY", "500000"))

# Approximate on-demand token pricing for Claude 3 Haiku (USD per 1K tokens).
BEDROCK_TOKEN_PRICING_USD_PER_1K = {
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
    "apac.anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
}

INSTANCE_SIZE_ORDER = [
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

# Usage-based approximation constants (USD).
USAGE_BASED_PRICING = {
    "s3_storage_per_gb": 0.023,
    "alb_hourly": 0.0225,
    "alb_lcu_hourly": 0.008,
    "cloudfront_data_per_gb": 0.085,
    "cloudfront_req_per_million": 0.75,
    "lambda_req_per_million": 0.20,
    "lambda_compute_per_gb_second": 0.0000166667,
    "api_gateway_req_per_million": 1.00,
    "dynamodb_req_per_million": 1.25,
    "elasticache_node_monthly": 25.0,
    "sqs_req_per_million": 0.40,
    "sns_req_per_million": 0.50,
    "ecs_baseline_monthly": 20.0,
    "eks_control_plane_monthly": 73.0,
    "nat_gateway_hourly": 0.045,
    "nat_gateway_data_per_gb": 0.045,
    "vpc_endpoint_monthly": 7.2,
    "cloudwatch_metrics_monthly": 10.0,
    "waf_web_acl_monthly": 5.0,
    "waf_req_per_million": 0.60,
    "route53_hosted_zone_monthly": 0.50,
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


@lru_cache(maxsize=128)
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


@lru_cache(maxsize=64)
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


def _usage_from_architecture(architecture: dict[str, Any]) -> dict[str, float]:
    usage = architecture.get("usage", {}) or {}
    return {
        "monthly_hours": float(max(1, min(744, int(usage.get("monthly_hours", HOURS_PER_MONTH_DEFAULT))))),
        "data_transfer_gb": float(max(0.0, usage.get("data_transfer_gb", 100))),
        "storage_gb": float(max(0.0, usage.get("storage_gb", 50))),
        "requests_million": float(max(0.0, usage.get("requests_million", 5))),
    }


def _estimate_usage_service_costs_usd(additional_services: list[str], usage: dict[str, float]) -> dict[str, float]:
    hours = usage["monthly_hours"]
    data_transfer_gb = usage["data_transfer_gb"]
    storage_gb = usage["storage_gb"]
    req_m = usage["requests_million"]
    costs: dict[str, float] = {}

    for service in sorted(set(additional_services)):
        if service in {"ec2", "rds", "bedrock", "total"}:
            continue
        if service == "s3":
            costs[service] = storage_gb * USAGE_BASED_PRICING["s3_storage_per_gb"]
        elif service == "alb":
            lcu = max(1.0, req_m / 10.0)
            costs[service] = hours * (
                USAGE_BASED_PRICING["alb_hourly"] + (USAGE_BASED_PRICING["alb_lcu_hourly"] * lcu)
            )
        elif service == "cloudfront":
            costs[service] = (data_transfer_gb * USAGE_BASED_PRICING["cloudfront_data_per_gb"]) + (
                req_m * USAGE_BASED_PRICING["cloudfront_req_per_million"]
            )
        elif service == "lambda":
            # Assume average 100ms duration with 512MB memory.
            compute_gb_seconds = req_m * 1_000_000 * 0.1 * 0.5
            costs[service] = (
                req_m * USAGE_BASED_PRICING["lambda_req_per_million"]
            ) + (compute_gb_seconds * USAGE_BASED_PRICING["lambda_compute_per_gb_second"])
        elif service == "apigateway":
            costs[service] = req_m * USAGE_BASED_PRICING["api_gateway_req_per_million"]
        elif service == "dynamodb":
            costs[service] = req_m * USAGE_BASED_PRICING["dynamodb_req_per_million"]
        elif service == "elasticache":
            costs[service] = USAGE_BASED_PRICING["elasticache_node_monthly"]
        elif service == "sqs":
            costs[service] = req_m * USAGE_BASED_PRICING["sqs_req_per_million"]
        elif service == "sns":
            costs[service] = req_m * USAGE_BASED_PRICING["sns_req_per_million"]
        elif service == "ecs":
            costs[service] = USAGE_BASED_PRICING["ecs_baseline_monthly"]
        elif service == "eks":
            costs[service] = USAGE_BASED_PRICING["eks_control_plane_monthly"]
        elif service == "nat-gateway":
            costs[service] = (
                hours * USAGE_BASED_PRICING["nat_gateway_hourly"]
                + data_transfer_gb * USAGE_BASED_PRICING["nat_gateway_data_per_gb"]
            )
        elif service == "vpc-endpoint":
            costs[service] = USAGE_BASED_PRICING["vpc_endpoint_monthly"]
        elif service == "cloudwatch":
            costs[service] = USAGE_BASED_PRICING["cloudwatch_metrics_monthly"]
        elif service == "waf":
            costs[service] = (
                USAGE_BASED_PRICING["waf_web_acl_monthly"] + req_m * USAGE_BASED_PRICING["waf_req_per_million"]
            )
        elif service == "route53":
            costs[service] = USAGE_BASED_PRICING["route53_hosted_zone_monthly"]
        else:
            costs[service] = 0.0

    return costs


def _estimate_with_pricing_api_usd(
    instance_type: str,
    ec2_count: int,
    rds_enabled: bool,
    rds_engine: str | None,
    region: str,
    hours_per_month: float,
) -> tuple[float, float, dict[str, Any]]:
    location = AWS_LOCATION_BY_REGION.get(region)
    if not location:
        raise ValueError(f"unsupported pricing region: {region}")

    ec2_hourly_usd = _query_ec2_hourly_usd(instance_type, location)
    if ec2_hourly_usd is None:
        raise ValueError(f"ec2 hourly pricing not found for {instance_type} in {location}")

    ec2_cost_usd = ec2_hourly_usd * hours_per_month * ec2_count

    rds_cost_usd = 0.0
    rds_hourly_usd = None
    if rds_enabled:
        if rds_engine not in {"mysql", "postgres"}:
            raise ValueError(f"unsupported rds engine: {rds_engine}")
        rds_hourly_usd = _query_rds_hourly_usd(rds_engine, location)
        if rds_hourly_usd is None:
            raise ValueError(f"rds hourly pricing not found for {rds_engine} in {location}")
        rds_cost_usd = rds_hourly_usd * hours_per_month

    assumptions = {
        "pricing_source": "aws_pricing_api",
        "pricing_region_endpoint": PRICING_REGION,
        "aws_location": location,
        "hours_per_month": hours_per_month,
        "ec2_hourly_usd": ec2_hourly_usd,
        "rds_hourly_usd": rds_hourly_usd if rds_enabled else 0,
        "rds_instance_type": "db.t3.micro" if rds_enabled else None,
    }
    return ec2_cost_usd, rds_cost_usd, assumptions


def _to_output_currency(usd_amount: float, currency: str, usd_to_krw: float) -> float:
    if currency == "KRW":
        return round(usd_amount * usd_to_krw, 2)
    return round(usd_amount, 2)


def _shift_instance_type(instance_type: str, step: int) -> str:
    if instance_type not in INSTANCE_SIZE_ORDER:
        return instance_type
    idx = INSTANCE_SIZE_ORDER.index(instance_type)
    shifted = max(0, min(len(INSTANCE_SIZE_ORDER) - 1, idx + step))
    return INSTANCE_SIZE_ORDER[shifted]


def _build_what_if_scenarios(
    architecture: dict[str, Any],
    output_currency: str,
    base_monthly_total: float,
) -> list[dict[str, Any]]:
    base_arch = deepcopy(architecture)
    base_usage = _usage_from_architecture(base_arch)
    base_ec2 = (base_arch.get("ec2", {}) or {}).get("instance_type", "t3.micro")
    base_count = int((base_arch.get("ec2", {}) or {}).get("count", 1))
    base_services = sorted(
        {
            str(s).lower()
            for s in base_arch.get("additional_services", [])
            if str(s).strip()
        }
    )

    def _scenario_payload(name: str, arch: dict[str, Any], notes: list[str]) -> dict[str, Any]:
        scenario_cost = estimate_monthly_cost(arch, include_optimization=False)
        total = float(scenario_cost["monthly_total"])
        delta = round(total - base_monthly_total, 2)
        delta_pct = round((delta / base_monthly_total) * 100, 2) if base_monthly_total > 0 else 0.0
        return {
            "name": name,
            "monthly_total": total,
            "delta_amount": delta,
            "delta_percent": delta_pct,
            "currency": output_currency,
            "notes": notes,
            "architecture": arch,
        }

    # Cost Saver scenario
    saver = deepcopy(base_arch)
    saver_notes: list[str] = []
    saver_ec2 = saver.get("ec2", {}) or {}
    saver_ec2["instance_type"] = _shift_instance_type(str(saver_ec2.get("instance_type", "t3.micro")), -1)
    if saver_ec2.get("instance_type") != base_ec2:
        saver_notes.append(f"Downsize EC2 to {saver_ec2['instance_type']}")
    if base_usage["requests_million"] < 1 and (saver.get("bedrock", {}) or {}).get("enabled"):
        saver["bedrock"] = {"enabled": False, "model": None}
        saver_notes.append("Disable Bedrock for very low AI traffic")
    saver_services = [s for s in base_services if not (s == "nat-gateway" and base_usage["data_transfer_gb"] < 20)]
    if len(saver_services) != len(base_services):
        saver_notes.append("Remove NAT Gateway for low transfer profile")
    saver["additional_services"] = saver_services
    saver["ec2"] = saver_ec2

    # Balanced scenario
    balanced = deepcopy(base_arch)
    balanced_notes: list[str] = []
    balanced_services = sorted(set(base_services + ["cloudwatch"]))
    if "cloudwatch" not in base_services:
        balanced_notes.append("Add CloudWatch for baseline observability")
    if balanced.get("public") and base_usage["requests_million"] >= 10 and "waf" not in balanced_services:
        balanced_services.append("waf")
        balanced_notes.append("Add WAF for public high-request endpoints")
    balanced["additional_services"] = sorted(set(balanced_services))

    # Performance scenario
    perf = deepcopy(base_arch)
    perf_notes: list[str] = []
    perf_ec2 = perf.get("ec2", {}) or {}
    perf_ec2["instance_type"] = _shift_instance_type(str(perf_ec2.get("instance_type", "t3.micro")), +1)
    perf_ec2["count"] = min(10, max(base_count, base_count + 1))
    perf["ec2"] = perf_ec2
    perf_notes.append(f"Upsize EC2 to {perf_ec2['instance_type']} and scale count to {perf_ec2['count']}")
    perf_services = sorted(set(base_services + ["alb", "cloudwatch"]))
    if perf.get("public") and "waf" not in perf_services:
        perf_services.append("waf")
    perf["additional_services"] = sorted(set(perf_services))
    if "alb" in perf["additional_services"]:
        perf_notes.append("Use ALB for safer distribution under load")
    if "waf" in perf["additional_services"]:
        perf_notes.append("Enable WAF for edge protection")

    return [
        _scenario_payload("cost_saver", saver, saver_notes),
        _scenario_payload("balanced", balanced, balanced_notes),
        _scenario_payload("performance", perf, perf_notes),
    ]


def _pick_recommended_scenario(
    scenarios: list[dict[str, Any]],
    usage: dict[str, float],
) -> str:
    if not scenarios:
        return "balanced"
    by_name = {str(s.get("name")): s for s in scenarios}
    if usage["requests_million"] >= 20:
        return "performance" if "performance" in by_name else scenarios[0]["name"]
    if usage["requests_million"] <= 2 and usage["data_transfer_gb"] <= 100:
        return "cost_saver" if "cost_saver" in by_name else scenarios[0]["name"]
    return "balanced" if "balanced" in by_name else scenarios[0]["name"]


def _build_optimization_recommendations(
    architecture: dict[str, Any],
    usage: dict[str, float],
    output_currency: str,
    base_monthly_total: float,
) -> dict[str, Any]:
    recommendations_add: list[str] = []
    recommendations_remove: list[str] = []
    cost_actions: list[str] = []

    arch_cost_optimized = deepcopy(architecture)
    ec2 = arch_cost_optimized.get("ec2", {}) or {}
    additional = sorted(
        {
            str(s).lower()
            for s in arch_cost_optimized.get("additional_services", [])
            if str(s).strip()
        }
    )
    arch_cost_optimized["additional_services"] = additional

    instance_type = str(ec2.get("instance_type", "t3.micro"))
    if (
        instance_type in INSTANCE_SIZE_ORDER
        and usage["requests_million"] <= 8
        and usage["data_transfer_gb"] <= 300
        and int(ec2.get("count", 1)) >= 1
    ):
        idx = INSTANCE_SIZE_ORDER.index(instance_type)
        if idx > 0:
            smaller = INSTANCE_SIZE_ORDER[idx - 1]
            ec2["instance_type"] = smaller
            arch_cost_optimized["ec2"] = ec2
            cost_actions.append(f"EC2 instance type downsize: {instance_type} -> {smaller}")

    if "nat-gateway" in additional and usage["data_transfer_gb"] < 20:
        additional = [s for s in additional if s != "nat-gateway"]
        arch_cost_optimized["additional_services"] = additional
        cost_actions.append("Remove NAT Gateway at very low transfer usage")

    bedrock = arch_cost_optimized.get("bedrock", {}) or {}
    if bedrock.get("enabled") and usage["requests_million"] < 1:
        arch_cost_optimized["bedrock"] = {"enabled": False, "model": None}
        arch_cost_optimized["additional_services"] = [
            s for s in arch_cost_optimized["additional_services"] if s != "bedrock"
        ]
        cost_actions.append("Disable Bedrock for very low request volume")

    base_services = {
        str(s).lower()
        for s in architecture.get("additional_services", [])
        if str(s).strip()
    }
    if "cloudwatch" not in base_services:
        recommendations_add.append("Add CloudWatch metrics/alarms for operational visibility")
    if architecture.get("public") and "waf" not in base_services and usage["requests_million"] >= 10:
        recommendations_add.append("Add AWS WAF to protect public endpoints")
    if architecture.get("public") and int((architecture.get("ec2", {}) or {}).get("count", 1)) >= 2 and "alb" not in base_services:
        recommendations_add.append("Add ALB for safer traffic distribution")
    if "nat-gateway" in base_services and usage["data_transfer_gb"] < 20:
        recommendations_remove.append("NAT Gateway may be unnecessary for this traffic level")
    if (architecture.get("bedrock", {}) or {}).get("enabled") and usage["requests_million"] < 1:
        recommendations_remove.append("Bedrock can be removed if AI workload remains near zero")

    optimized_cost = estimate_monthly_cost(arch_cost_optimized, include_optimization=False)
    optimized_total = float(optimized_cost["monthly_total"])
    savings = round(base_monthly_total - optimized_total, 2)
    savings_pct = round((savings / base_monthly_total) * 100, 2) if base_monthly_total > 0 else 0.0

    scenarios = _build_what_if_scenarios(
        architecture=architecture,
        output_currency=output_currency,
        base_monthly_total=base_monthly_total,
    )
    recommended = _pick_recommended_scenario(scenarios, usage)
    return {
        "cost_optimization": {
            "actions": cost_actions,
            "optimized_architecture": arch_cost_optimized,
            "optimized_monthly_total": optimized_total,
            "savings_amount": max(0.0, savings),
            "savings_percent": max(0.0, savings_pct),
            "currency": output_currency,
        },
        "quality_recommendations": {
            "add": recommendations_add,
            "remove": recommendations_remove,
        },
        "scenarios": scenarios,
        "recommended_scenario": recommended,
    }


def estimate_monthly_cost(architecture: dict[str, Any], *, include_optimization: bool = True) -> dict[str, Any]:
    ec2 = architecture.get("ec2", {})
    rds = architecture.get("rds", {})
    bedrock = architecture.get("bedrock", {})
    additional_services = [str(s).lower() for s in architecture.get("additional_services", []) if str(s).strip()]
    region = architecture.get("region", "ap-northeast-2")
    usage = _usage_from_architecture(architecture)

    instance_type = ec2.get("instance_type", "t3.micro")
    ec2_count = int(ec2.get("count", 1))
    rds_enabled = bool(rds.get("enabled", False))
    rds_engine = rds.get("engine")
    bedrock_enabled = bool(bedrock.get("enabled", False))
    bedrock_model = bedrock.get("model") or "anthropic.claude-3-haiku-20240307-v1:0"

    pricing_error = None
    try:
        ec2_cost_usd, rds_cost_usd, pricing_assumptions = _estimate_with_pricing_api_usd(
            instance_type=instance_type,
            ec2_count=ec2_count,
            rds_enabled=rds_enabled,
            rds_engine=rds_engine,
            region=region,
            hours_per_month=usage["monthly_hours"],
        )
    except (ClientError, BotoCoreError, ValueError) as e:
        pricing_error = str(e)
        region_factor = REGION_FACTOR.get(region, 1.00)
        ec2_unit_base_krw = EC2_BASE_MONTHLY_KRW.get(instance_type, EC2_BASE_MONTHLY_KRW["t3.micro"])
        ec2_cost_usd = (ec2_unit_base_krw * region_factor * ec2_count) / USD_TO_KRW_DEFAULT

        rds_cost_usd = 0.0
        rds_unit_krw = 0.0
        if rds_enabled:
            rds_unit_base_krw = RDS_BASE_MONTHLY_KRW.get(rds_engine, RDS_BASE_MONTHLY_KRW["mysql"])
            rds_unit_krw = rds_unit_base_krw * region_factor
            rds_cost_usd = rds_unit_krw / USD_TO_KRW_DEFAULT

        pricing_assumptions = {
            "pricing_source": "fallback_static_table",
            "region_factor": region_factor,
            "ec2_unit_krw": round(ec2_unit_base_krw * region_factor, 2),
            "rds_unit_krw": round(rds_unit_krw, 2) if rds_enabled else 0,
            "pricing_error": pricing_error,
        }

    bedrock_cost_usd = 0.0
    if bedrock_enabled:
        model_pricing = BEDROCK_TOKEN_PRICING_USD_PER_1K.get(bedrock_model)
        if model_pricing:
            bedrock_input_cost_usd = (BEDROCK_INPUT_TOKENS_MONTHLY / 1000.0) * model_pricing["input"]
            bedrock_output_cost_usd = (BEDROCK_OUTPUT_TOKENS_MONTHLY / 1000.0) * model_pricing["output"]
            bedrock_cost_usd = bedrock_input_cost_usd + bedrock_output_cost_usd

    usage_service_costs_usd = _estimate_usage_service_costs_usd(additional_services, usage)
    additional_services_total_usd = sum(usage_service_costs_usd.values())

    total_usd = ec2_cost_usd + rds_cost_usd + bedrock_cost_usd + additional_services_total_usd
    output_currency = OUTPUT_CURRENCY if OUTPUT_CURRENCY in {"USD", "KRW"} else "USD"
    breakdown = {
        "ec2": _to_output_currency(ec2_cost_usd, output_currency, USD_TO_KRW_DEFAULT),
        "rds": _to_output_currency(rds_cost_usd, output_currency, USD_TO_KRW_DEFAULT),
        "bedrock": _to_output_currency(bedrock_cost_usd, output_currency, USD_TO_KRW_DEFAULT),
        **{
            service: _to_output_currency(cost_usd, output_currency, USD_TO_KRW_DEFAULT)
            for service, cost_usd in usage_service_costs_usd.items()
        },
        "total": _to_output_currency(total_usd, output_currency, USD_TO_KRW_DEFAULT),
    }

    assumptions = {
        "currency": output_currency,
        "secondary_currency": "KRW" if output_currency == "USD" else "USD",
        "usd_to_krw": USD_TO_KRW_DEFAULT,
        "region": region,
        "ec2_type": instance_type,
        "ec2_count": ec2_count,
        "rds_enabled": rds_enabled,
        "rds_engine": rds_engine,
        "bedrock_enabled": bedrock_enabled,
        "bedrock_model": bedrock_model if bedrock_enabled else None,
        "bedrock_input_tokens_monthly": BEDROCK_INPUT_TOKENS_MONTHLY if bedrock_enabled else 0,
        "bedrock_output_tokens_monthly": BEDROCK_OUTPUT_TOKENS_MONTHLY if bedrock_enabled else 0,
        "usage": usage,
        "additional_services": sorted(set(additional_services)),
        "additional_service_costs_usd": {k: round(v, 4) for k, v in usage_service_costs_usd.items()},
        "pricing_version": "v4-usage-based",
        "monthly_total_usd": round(total_usd, 4),
        "monthly_total_krw": round(total_usd * USD_TO_KRW_DEFAULT, 2),
        **pricing_assumptions,
    }

    if include_optimization:
        assumptions["optimization"] = _build_optimization_recommendations(
            architecture=architecture,
            usage=usage,
            output_currency=output_currency,
            base_monthly_total=breakdown["total"],
        )

    return {
        "currency": output_currency,
        "region": region,
        "assumptions": assumptions,
        "monthly_total": breakdown["total"],
        "breakdown": breakdown,
    }
