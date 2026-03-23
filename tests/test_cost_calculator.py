from __future__ import annotations

from app.cost_calculator import estimate_monthly_cost


def test_cost_with_rds() -> None:
    architecture = {
        "vpc": True,
        "ec2": {"count": 2, "instance_type": "t3.micro"},
        "rds": {"enabled": True, "engine": "mysql"},
        "public": True,
        "region": "ap-northeast-2",
    }
    out = estimate_monthly_cost(architecture)
    assert out["currency"] == "KRW"
    assert out["monthly_total"] == 42000
    assert out["breakdown"]["ec2"] == 24000
    assert out["breakdown"]["rds"] == 18000
    assert out["assumptions"]["pricing_version"] == "v2-table"


def test_cost_without_rds() -> None:
    architecture = {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.small"},
        "rds": {"enabled": False, "engine": None},
        "public": False,
        "region": "ap-northeast-2",
    }
    out = estimate_monthly_cost(architecture)
    assert out["monthly_total"] == 22000
    assert out["breakdown"]["rds"] == 0

