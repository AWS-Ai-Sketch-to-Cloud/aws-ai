from app.terraform_generator import generate_terraform_from_architecture


def test_generator_uses_region_agnostic_ami_lookup() -> None:
    terraform_code = generate_terraform_from_architecture(
        {
            "region": "us-east-1",
            "ec2": {"count": 1, "instance_type": "t3.micro"},
        }
    )

    assert 'data "aws_ami" "amazon_linux"' in terraform_code
    assert "ami           = data.aws_ami.amazon_linux.id" in terraform_code
    assert "ami-0c9c942bd7bf113a2" not in terraform_code


def test_generator_creates_two_subnets_for_rds() -> None:
    terraform_code = generate_terraform_from_architecture(
        {
            "region": "us-east-1",
            "rds": {"enabled": True, "engine": "mysql"},
        }
    )

    assert 'resource "aws_subnet" "public"' in terraform_code
    assert 'resource "aws_subnet" "private"' in terraform_code
    assert "data.aws_availability_zones.available.names[0]" in terraform_code
    assert "data.aws_availability_zones.available.names[1]" in terraform_code
    assert "subnet_ids = [aws_subnet.public.id, aws_subnet.private.id]" in terraform_code


def test_generator_uses_unique_suffix_for_named_resources() -> None:
    terraform_code = generate_terraform_from_architecture(
        {
            "region": "us-east-1",
            "rds": {"enabled": True, "engine": "mysql"},
            "bedrock": {"enabled": True},
            "additional_services": ["sns", "sqs", "dynamodb", "s3"],
        }
    )

    assert 'resource "random_string" "name_suffix"' in terraform_code
    assert 'name = "app-bedrock-role-${random_string.name_suffix.result}"' in terraform_code
    assert 'name = "bedrock-invoke-policy-${random_string.name_suffix.result}"' in terraform_code
    assert 'name       = "main-db-subnet-group-${random_string.name_suffix.result}"' in terraform_code
    assert 'identifier             = "main-db-${random_string.name_suffix.result}"' in terraform_code
    assert 'name = "stc-app-events-${random_string.name_suffix.result}"' in terraform_code
