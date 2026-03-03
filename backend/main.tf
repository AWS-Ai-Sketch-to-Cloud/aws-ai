# main.tf

# Test bucket to verify localstack connection
resource "aws_s3_bucket" "test_bucket" {
  bucket = "sketch-to-cloud-test-bucket"
}
