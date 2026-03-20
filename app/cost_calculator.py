from __future__ import annotations

from typing import Any


EC2_MONTHLY_KRW = {
    "t3.micro": 12000,
    "t3.small": 22000,
    "t3.medium": 43000,
}

RDS_MONTHLY_KRW = {
    "mysql": 18000,
    "postgres": 20000,
}


def estimate_monthly_cost(architecture: dict[str, Any]) -> dict[str, Any]:
    ec2 = architecture.get("ec2", {})
    rds = architecture.get("rds", {})
    region = architecture.get("region", "ap-northeast-2")

    instance_type = ec2.get("instance_type", "t3.micro")
    ec2_count = int(ec2.get("count", 1))
    rds_enabled = bool(rds.get("enabled", False))
    rds_engine = rds.get("engine")

    ec2_unit = EC2_MONTHLY_KRW.get(instance_type, EC2_MONTHLY_KRW["t3.micro"])
    ec2_cost = ec2_unit * ec2_count

    rds_cost = 0
    if rds_enabled:
        rds_cost = RDS_MONTHLY_KRW.get(rds_engine, RDS_MONTHLY_KRW["mysql"])

    total = ec2_cost + rds_cost
    assumptions = {
        "currency": "KRW",
        "region": region,
        "ec2_type": instance_type,
        "ec2_count": ec2_count,
        "rds_enabled": rds_enabled,
        "rds_engine": rds_engine,
        "hours_per_month": 730,
        "pricing_version": "v1-static",
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

