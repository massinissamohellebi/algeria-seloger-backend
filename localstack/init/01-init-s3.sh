#!/bin/bash
# LocalStack init hook (runs once the S3 service is ready). Creates the photos
# bucket and makes objects publicly readable so the browser can load uploaded
# photos without signed URLs — matches the dev-only S3_PUBLIC_BASE_URL wiring.
set -euo pipefail

BUCKET="seloger-photos"

awslocal s3 mb "s3://${BUCKET}" || true

awslocal s3api put-bucket-policy --bucket "${BUCKET}" --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::seloger-photos/*"
    }
  ]
}'

echo "LocalStack: bucket ${BUCKET} ready (public read)."
