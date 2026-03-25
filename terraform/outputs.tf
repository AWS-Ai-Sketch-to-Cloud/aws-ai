output "aws_region" {
  value       = var.aws_region
  description = "Deployment region."
}

output "mode" {
  value       = "bedrock-only"
  description = "This Terraform stack does not create AWS infra resources."
}
