from __future__ import annotations

from app.terraform_generator import generate_terraform_from_architecture


def test_terraform_includes_rds_when_enabled() -> None:
    architecture = {
        "vpc": True,
        "ec2": {"count": 2, "instance_type": "t3.micro"},
        "rds": {"enabled": True, "engine": "postgres"},
        "public": True,
        "region": "ap-northeast-2",
    }
    tf = generate_terraform_from_architecture(architecture)
    assert 'resource "aws_instance" "app"' in tf
    assert "count         = 2" in tf
    assert 'engine                 = "postgres"' in tf


def test_terraform_excludes_rds_when_disabled() -> None:
    architecture = {
        "vpc": True,
        "ec2": {"count": 1, "instance_type": "t3.small"},
        "rds": {"enabled": False, "engine": None},
        "public": False,
        "region": "us-east-1",
    }
    tf = generate_terraform_from_architecture(architecture)
    assert 'resource "aws_instance" "app"' in tf
    assert "count         = 1" in tf
    assert 'resource "aws_db_instance" "main"' not in tf

