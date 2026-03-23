from __future__ import annotations

from typing import Any


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


def estimate_monthly_cost(architecture: dict[str, Any]) -> dict[str, Any]:
    ec2 = architecture.get("ec2", {})
    rds = architecture.get("rds", {})
    region = architecture.get("region", "ap-northeast-2")

    instance_type = ec2.get("instance_type", "t3.micro")
    ec2_count = int(ec2.get("count", 1))
    rds_enabled = bool(rds.get("enabled", False))
    rds_engine = rds.get("engine")
    region_factor = REGION_FACTOR.get(region, 1.00)

    ec2_unit_base = EC2_BASE_MONTHLY_KRW.get(instance_type, EC2_BASE_MONTHLY_KRW["t3.micro"])
    ec2_unit = round(ec2_unit_base * region_factor)
    ec2_cost = ec2_unit * ec2_count

    rds_cost = 0
    if rds_enabled:
        rds_unit_base = RDS_BASE_MONTHLY_KRW.get(rds_engine, RDS_BASE_MONTHLY_KRW["mysql"])
        rds_cost = round(rds_unit_base * region_factor)

    total = ec2_cost + rds_cost
    assumptions = {
        "currency": "KRW",
        "region": region,
        "ec2_type": instance_type,
        "ec2_count": ec2_count,
        "rds_enabled": rds_enabled,
        "rds_engine": rds_engine,
        "region_factor": region_factor,
        "ec2_unit_krw": ec2_unit,
        "rds_unit_krw": rds_cost if rds_enabled else 0,
        "hours_per_month": 730,
        "pricing_version": "v2-table",
    }
    breakdown = {
        "ec2": ec2_cost,
        "rds": rds_cost,
        "total": total,
    }
    return {
        "currency": "KRW",
        "region": region,
        "assumptions": assumptions,
        "monthly_total": total,
        "breakdown": breakdown,
    }

