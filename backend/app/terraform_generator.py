from __future__ import annotations

from typing import Any


def _bool_tf(value: bool) -> str:
    return "true" if value else "false"


def generate_terraform_from_architecture(architecture: dict[str, Any]) -> str:
    ec2 = architecture.get("ec2", {})
    rds = architecture.get("rds", {})
    bedrock = architecture.get("bedrock", {})
    public = bool(architecture.get("public", False))
    region = architecture.get("region", "ap-northeast-2")
    ec2_count = int(ec2.get("count", 1))
    instance_type = ec2.get("instance_type", "t3.micro")
    rds_enabled = bool(rds.get("enabled", False))
    rds_engine = rds.get("engine")
    bedrock_enabled = bool(bedrock.get("enabled", False))
    bedrock_model = bedrock.get("model") or "anthropic.claude-3-haiku-20240307-v1:0"
    additional_services = sorted({str(s).lower() for s in architecture.get("additional_services", []) if str(s).strip()})
    ingress_cidr = "0.0.0.0/0" if public else "10.0.0.0/16"

    lines: list[str] = []
    lines.extend(
        [
            'terraform {',
            '  required_providers {',
            '    aws = {',
            '      source  = "hashicorp/aws"',
            '      version = "~> 5.0"',
            "    }",
            '    random = {',
            '      source  = "hashicorp/random"',
            '      version = "~> 3.6"',
            "    }",
            "  }",
            "}",
            "",
            f'provider "aws" {{',
            f'  region = "{region}"',
            "}",
            "",
            'data "aws_availability_zones" "available" {',
            "  state = \"available\"",
            "}",
            "",
            'data "aws_ami" "amazon_linux" {',
            "  most_recent = true",
            "  owners      = [\"amazon\"]",
            "",
            "  filter {",
            '    name   = "name"',
            '    values = ["al2023-ami-2023.*-x86_64"]',
            "  }",
            "",
            "  filter {",
            '    name   = "root-device-type"',
            '    values = ["ebs"]',
            "  }",
            "",
            "  filter {",
            '    name   = "virtualization-type"',
            '    values = ["hvm"]',
            "  }",
            "}",
            "",
            'resource "random_string" "name_suffix" {',
            "  length  = 6",
            "  upper   = false",
            "  special = false",
            '  numeric = true',
            "}",
            "",
            'resource "aws_vpc" "main" {',
            '  cidr_block           = "10.0.0.0/16"',
            "  enable_dns_support   = true",
            "  enable_dns_hostnames = true",
            "}",
            "",
            'resource "aws_subnet" "public" {',
            "  vpc_id                  = aws_vpc.main.id",
            '  cidr_block              = "10.0.1.0/24"',
            "  availability_zone       = data.aws_availability_zones.available.names[0]",
            f"  map_public_ip_on_launch = {_bool_tf(public)}",
            "}",
            "",
            'resource "aws_subnet" "private" {',
            "  vpc_id                  = aws_vpc.main.id",
            '  cidr_block              = "10.0.2.0/24"',
            "  availability_zone       = data.aws_availability_zones.available.names[1]",
            "  map_public_ip_on_launch = false",
            "}",
            "",
            'resource "aws_security_group" "app_sg" {',
            '  name   = "app-sg-${random_string.name_suffix.result}"',
            "  vpc_id = aws_vpc.main.id",
            "",
            "  ingress {",
            "    from_port   = 80",
            "    to_port     = 80",
            '    protocol    = "tcp"',
            f'    cidr_blocks = ["{ingress_cidr}"]',
            "  }",
            "",
            "  egress {",
            "    from_port   = 0",
            "    to_port     = 0",
            '    protocol    = "-1"',
            '    cidr_blocks = ["0.0.0.0/0"]',
            "  }",
            "}",
            "",
            'resource "aws_instance" "app" {',
            f"  count         = {ec2_count}",
            "  ami           = data.aws_ami.amazon_linux.id",
            f'  instance_type = "{instance_type}"',
            "  subnet_id     = aws_subnet.public.id",
            "  vpc_security_group_ids = [aws_security_group.app_sg.id]",
            "}",
            "",
        ]
    )

    if rds_enabled:
        engine = "postgres" if rds_engine == "postgres" else "mysql"
        lines.extend(
            [
                'resource "aws_db_subnet_group" "main" {',
                '  name       = "main-db-subnet-group-${random_string.name_suffix.result}"',
                "  subnet_ids = [aws_subnet.public.id, aws_subnet.private.id]",
                "}",
                "",
                'resource "aws_db_instance" "main" {',
                '  identifier             = "main-db-${random_string.name_suffix.result}"',
                f'  engine                 = "{engine}"',
                '  instance_class         = "db.t3.micro"',
                "  allocated_storage      = 20",
                '  username               = "admin"',
                '  password               = "change-me-please"',
                "  skip_final_snapshot    = true",
                "  db_subnet_group_name   = aws_db_subnet_group.main.name",
                "  vpc_security_group_ids = [aws_security_group.app_sg.id]",
                "}",
                "",
            ]
        )

    if bedrock_enabled:
        lines.extend(
            [
                '# Bedrock access policy for application role',
                'resource "aws_iam_role" "app_bedrock_role" {',
                '  name = "app-bedrock-role-${random_string.name_suffix.result}"',
                "",
                "  assume_role_policy = jsonencode({",
                '    Version = "2012-10-17"',
                "    Statement = [{",
                '      Effect = "Allow"',
                "      Principal = { Service = \"ec2.amazonaws.com\" }",
                '      Action = "sts:AssumeRole"',
                "    }]",
                "  })",
                "}",
                "",
                'resource "aws_iam_policy" "bedrock_invoke" {',
                '  name = "bedrock-invoke-policy-${random_string.name_suffix.result}"',
                "  policy = jsonencode({",
                '    Version = "2012-10-17"',
                "    Statement = [{",
                '      Effect = "Allow"',
                "      Action = [",
                '        "bedrock:InvokeModel",',
                '        "bedrock:InvokeModelWithResponseStream",',
                '        "bedrock:ListFoundationModels"',
                "      ]",
                '      Resource = "*"',
                "    }]",
                "  })",
                "}",
                "",
                'resource "aws_iam_role_policy_attachment" "app_bedrock_attach" {',
                "  role       = aws_iam_role.app_bedrock_role.name",
                "  policy_arn = aws_iam_policy.bedrock_invoke.arn",
                "}",
                "",
                "# Selected Bedrock model",
                'locals {',
                f'  bedrock_model_id = "{bedrock_model}"',
                "}",
                "",
            ]
        )

    if "s3" in additional_services:
        lines.extend(
            [
                'resource "aws_s3_bucket" "app_assets" {',
                '  bucket = "stc-assets-${random_string.name_suffix.result}-${random_id.bucket_suffix.hex}"',
                "}",
                "",
                'resource "random_id" "bucket_suffix" {',
                "  byte_length = 4",
                "}",
                "",
            ]
        )

    if "dynamodb" in additional_services:
        lines.extend(
            [
                'resource "aws_dynamodb_table" "app_state" {',
                '  name         = "stc-app-state-${random_string.name_suffix.result}"',
                '  billing_mode = "PAY_PER_REQUEST"',
                '  hash_key     = "pk"',
                "",
                "  attribute {",
                '    name = "pk"',
                '    type = "S"',
                "  }",
                "}",
                "",
            ]
        )

    if "sqs" in additional_services:
        lines.extend(
            [
                'resource "aws_sqs_queue" "app_queue" {',
                '  name = "stc-app-queue-${random_string.name_suffix.result}"',
                "}",
                "",
            ]
        )

    if "sns" in additional_services:
        lines.extend(
            [
                'resource "aws_sns_topic" "app_events" {',
                '  name = "stc-app-events-${random_string.name_suffix.result}"',
                "}",
                "",
            ]
        )

    unsupported = [s for s in additional_services if s not in {"bedrock", "s3", "dynamodb", "sqs", "sns"}]
    if unsupported:
        unsupported_hcl = "[" + ", ".join(f'"{s}"' for s in unsupported) + "]"
        lines.extend(
            [
                "# Additional service requirements captured from prompt",
                f"locals {{ additional_service_requirements = {unsupported_hcl} }}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"
