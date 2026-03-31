from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cost_calculator import estimate_monthly_cost


def _case_static_site() -> dict:
    return {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.micro"},
        "rds": {"enabled": False, "engine": None},
        "bedrock": {"enabled": False, "model": None},
        "additional_services": ["s3", "cloudfront", "route53"],
        "usage": {"monthly_hours": 730, "data_transfer_gb": 30, "storage_gb": 10, "requests_million": 1},
        "public": True,
        "region": "ap-northeast-2",
    }


def _case_api_with_db() -> dict:
    return {
        "vpc": True,
        "ec2": {"count": 2, "instance_type": "t3.small"},
        "rds": {"enabled": True, "engine": "postgres"},
        "bedrock": {"enabled": False, "model": None},
        "additional_services": ["alb", "cloudwatch"],
        "usage": {"monthly_hours": 730, "data_transfer_gb": 150, "storage_gb": 80, "requests_million": 6},
        "public": True,
        "region": "ap-northeast-2",
    }


def _case_serverless_ai() -> dict:
    return {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.micro"},
        "rds": {"enabled": False, "engine": None},
        "bedrock": {"enabled": True, "model": "anthropic.claude-3-haiku-20240307-v1:0"},
        "additional_services": ["lambda", "apigateway", "cloudwatch"],
        "usage": {"monthly_hours": 730, "data_transfer_gb": 60, "storage_gb": 20, "requests_million": 8},
        "public": True,
        "region": "ap-northeast-2",
    }


def run() -> int:
    cases = [
        ("static_site", _case_static_site()),
        ("api_with_db", _case_api_with_db()),
        ("serverless_ai", _case_serverless_ai()),
    ]

    failures: list[str] = []
    totals: dict[str, float] = {}
    for name, arch in cases:
        result = estimate_monthly_cost(arch)
        monthly_total = float(result.get("monthly_total", 0))
        breakdown = result.get("breakdown", {}) or {}
        assumptions = result.get("assumptions", {}) or {}
        totals[name] = monthly_total

        if monthly_total <= 0:
            failures.append(f"{name}: monthly_total <= 0")
        if "total" not in breakdown:
            failures.append(f"{name}: breakdown.total missing")
        if assumptions.get("region") != arch["region"]:
            failures.append(f"{name}: region mismatch in assumptions")
        if assumptions.get("pricing_source") not in {"aws_pricing_api", "fallback_static_table"}:
            failures.append(f"{name}: invalid pricing_source")

    if totals["api_with_db"] <= totals["static_site"]:
        failures.append("api_with_db should cost more than static_site")
    if totals["serverless_ai"] <= 0:
        failures.append("serverless_ai total should be positive")

    if failures:
        print("[FAIL] cost sanity check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("[PASS] cost sanity check")
    for name, total in totals.items():
        print(f"- {name}: {total}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cost sanity checks.")
    parser.parse_args()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
