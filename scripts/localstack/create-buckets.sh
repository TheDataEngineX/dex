#!/bin/bash
# Create the test S3 bucket in LocalStack on startup.
awslocal s3 mb s3://dex-test-bucket
echo "Created S3 bucket: dex-test-bucket"
