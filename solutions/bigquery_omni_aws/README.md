# BigQuery Omni for AWS S3 - Deployment Solution

This solution provisions a complete **BigQuery Omni** connection and dataset architecture in Google Cloud to query data stored in **AWS S3** directly from BigQuery without data movement or cross-cloud migration.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD                         │
│                                                         │
│   ┌───────────────────┐        ┌────────────────────┐   │
│   │ BigQuery Studio   │───────►│ BigQuery Omni      │   │
│   │ Query Console     │        │ Dataset            │   │
│   └───────────────────┘        └─────────┬──────────┘   │
│                                          │              │
│                                ┌─────────▼──────────┐   │
│                                │ BQ Omni Connection │   │
│                                │ (AWS IAM Access)   │   │
│                                └─────────┬──────────┘   │
└────────────────────────────────────────┼────────────────┘
                                         │
                        Cross-Cloud IAM Trust Handshake
                                         │
┌────────────────────────────────────────▼────────────────┐
│                     AWS ACCOUNT                         │
│                                                         │
│   ┌───────────────────┐        ┌────────────────────┐   │
│   │ AWS IAM Role      │───────►│ AWS S3 Bucket      │   │
│   │ (S3 Read Policy)  │        │ (Parquet, CSV, etc)│   │
│   └───────────────────┘        └────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Step 1: Copy Configuration Template
Copy `terraform.tfvars.sample` to `terraform.tfvars`:
```bash
cp terraform.tfvars.sample terraform.tfvars
```

### Step 2: Update Placeholders in `terraform.tfvars`
Edit `terraform.tfvars` and supply:
* `project_id`: Your Google Cloud Project ID.
* `omni_location`: The BigQuery Omni region matching your AWS S3 region (e.g. `aws-us-east-1`).
* `aws_iam_role_arn`: The AWS IAM Role ARN created in AWS to access S3 (e.g., `arn:aws:iam::123456789012:role/nyl-bq-omni-s3-role`).
* `external_tables`: Define S3 bucket paths (`s3://my-bucket/path/*`) and formats (`PARQUET`, `CSV`, `JSON`, `ORC`, `AVRO`).

### Step 3: Run Terraform Deployment
```bash
terraform init
terraform apply
```

---

## 🔐 Critical Step 4: AWS IAM Role Trust Relationship Handshake

After running `terraform apply`, Terraform will output the **GCP BigQuery Omni Identity ID**:

```hcl
aws_identity_id = "012345678901234567890"
```

You **MUST** add this `aws_identity_id` to your **AWS IAM Role's Trust Policy** in your AWS Account console so AWS allows BigQuery Omni to assume the role.

### AWS IAM Role Trust Policy Template:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "accounts.google.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "accounts.google.com:sub": "<AWS_IDENTITY_ID_FROM_TERRAFORM_OUTPUT>"
        }
      }
    }
  ]
}
```

### AWS IAM Role S3 Permissions Policy:
Attach this policy to the AWS IAM Role to grant access to the target S3 bucket:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::nyl-enterprise-data-bucket"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::nyl-enterprise-data-bucket/*"
    }
  ]
}
```

---

## 🧪 Step 5: Querying S3 Data directly in BigQuery

Once the AWS Trust Policy is updated, you can immediately run standard SQL queries in BigQuery Studio against your AWS S3 data:

```sql
SELECT * 
FROM `my-gcp-data-project-id.nyl_bq_omni_aws_s3_dataset.s3_sales_transactions_parquet`
LIMIT 100;
```
