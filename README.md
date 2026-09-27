**This is a simple demonstration of building a simple data lake solution with AWS.**

Steps:
1. Setup AWS services e.g. S3 buckets with Terraform.
2. Data ingestion. Collect data by calling API. Data collected are Hang Sang Index and Temperature in the past 10 years.
3. ETL. ETL with AWS Glue, from a S3 raw bucket, transformed, then load to a processed S3 bucket.
4. DDL with Athena.
5. Generate dashboard with Plotly and host it on AWS S3.
