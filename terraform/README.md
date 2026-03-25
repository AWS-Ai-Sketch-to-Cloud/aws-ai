# Terraform Infra (aws-ai)

This folder is configured for Bedrock-only local mode for the current `aws-ai` project.

## What gets created

- No AWS infrastructure resources are created.
- Terraform is kept only for credential/region wiring consistency.

## Prerequisites

- Terraform `>= 1.6`
- AWS credentials configured (environment variables or AWS CLI profile)
- Region/model access enabled in Bedrock

## First-time setup

1. Create var file:

```powershell
Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars
```

2. Edit only `aws_region` if needed.

## Deploy

```powershell
./scripts/infra_deploy.ps1
```

This will run `init/plan/apply`, but apply results in no infrastructure resources.

## Destroy

```powershell
./scripts/infra_destroy.ps1
```

## Notes

- Current state backend is local (`terraform.tfstate` in this folder).
- Deploy/destroy scripts automatically import AWS keys from `backend/.env` if present.
