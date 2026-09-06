terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# 1. Set the region as discussed
provider "aws" {
  region = "us-east-1"
}

# Generate a random 4-byte string to ensure S3 bucket names are globally unique
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ==========================================
# 2. DATA LAKE S3 BUCKETS
# ==========================================
resource "aws_s3_bucket" "raw_zone" {
  bucket        = "portfolio-raw-zone-${random_id.bucket_suffix.hex}"
  force_destroy = true # Allows Terraform to delete the bucket even if it contains files
}

resource "aws_s3_bucket" "processed_zone" {
  bucket        = "portfolio-processed-zone-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

# ==========================================
# 3. GLUE DATA CATALOG & IAM ROLE
# ==========================================
resource "aws_glue_catalog_database" "hk_weather_finance_db" {
  name = "hk_weather_finance_db"
}

# IAM Role required for the Glue job to read/write to S3 and the Catalog
resource "aws_iam_role" "glue_role" {
  name = "portfolio_glue_etl_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_s3_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# ==========================================
# 4. PLOTLY DASHBOARD (STATIC WEBSITE)
# ==========================================
resource "aws_s3_bucket" "dashboard_website" {
  bucket        = "portfolio-dashboard-site-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

# Configure the bucket to act as a web server
resource "aws_s3_bucket_website_configuration" "dashboard_config" {
  bucket = aws_s3_bucket.dashboard_website.id
  index_document {
    suffix = "index.html"
  }
}

# Override AWS default block to allow the bucket to be public
resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket                  = aws_s3_bucket.dashboard_website.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Attach policy giving the public permission to view the HTML file
resource "aws_s3_bucket_policy" "public_read_policy" {
  depends_on = [aws_s3_bucket_public_access_block.public_access]
  bucket     = aws_s3_bucket.dashboard_website.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid       = "PublicReadGetObject",
      Effect    = "Allow",
      Principal = "*",
      Action    = "s3:GetObject",
      Resource  = "${aws_s3_bucket.dashboard_website.arn}/*"
    }]
  })
}

# ==========================================
# 5. OUTPUTS (Printed to terminal after apply)
# ==========================================
output "dashboard_url" {
  description = "The permanent URL to view your Plotly dashboard"
  value       = "http://${aws_s3_bucket_website_configuration.dashboard_config.website_endpoint}"
}

output "raw_bucket_name" {
  value = aws_s3_bucket.raw_zone.bucket
}

output "processed_bucket_name" {
  value = aws_s3_bucket.processed_zone.bucket
}

output "glue_role_arn" {
  value = aws_iam_role.glue_role.arn
}