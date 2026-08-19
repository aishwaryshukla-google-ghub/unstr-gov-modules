#!/usr/bin/env bash
# =============================================================================
# Deployment Script for Dataplex Catalog Sync (Cloud Run Function / Service)
# =============================================================================
set -euo pipefail

# Configuration Defaults
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || echo "databricks-playground-497321")}"
REGION="${2:-us-central1}"
SERVICE_NAME="dataplex-catalog-sync"
SERVICE_ACCOUNT_NAME="dataplex-catalog-sync-sa"
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "================================================================="
echo " Deploying Dataplex Catalog Sync Service"
echo " Project:  ${PROJECT_ID}"
echo " Region:   ${REGION}"
echo " Service:  ${SERVICE_NAME}"
echo "================================================================="

# 1. Enable Required APIs
echo "[1/5] Enabling GCP APIs..."
gcloud services enable \
  dataplex.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create Service Account if not existing
echo "[2/5] Setting up Service Account (${SA_EMAIL})..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Dataplex Catalog Sync Service Account" \
    --project="${PROJECT_ID}"
fi

# 3. Grant Required Roles to Service Account
echo "[3/5] Assigning IAM roles to ${SA_EMAIL}..."
ROLES=(
  "roles/dataplex.admin"
  "roles/dataplex.catalogEditor"
  "roles/storage.objectViewer"
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None >/dev/null
done

# 4. Deploy to Cloud Run (Cloud Run Function Gen 2 compatible)
echo "[4/5] Deploying Cloud Run Service..."
gcloud run deploy "${SERVICE_NAME}" \
  --source="." \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SA_EMAIL}" \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},LOCATION=${REGION}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=120s

# 5. Output Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

echo "================================================================="
echo " Deployment Complete!"
echo " Service URL: ${SERVICE_URL}"
echo ""
echo " You can now update remote_function.sql with this endpoint:"
echo "   endpoint = '${SERVICE_URL}'"
echo "================================================================="
