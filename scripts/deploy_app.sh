#!/usr/bin/env bash
# Trigger the Cloud Build app-only CI/CD pipeline manually for dev or prod.
# Usage: ./scripts/deploy_app.sh [dev|prod] [GCP_PROJECT_ID]
set -euo pipefail

ENV_NAME="${1:-prod}"
PROJECT_ID="${2:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="europe-west4"

if [[ "${ENV_NAME}" != "dev" && "${ENV_NAME}" != "prod" ]]; then
  echo "Error: environment must be 'dev' or 'prod' (got '${ENV_NAME}')"
  exit 1
fi

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Usage: $0 [dev|prod] <GCP_PROJECT_ID>"
  exit 1
fi

echo "==> Running Cloud Build app CI/CD pipeline for env='${ENV_NAME}' on project='${PROJECT_ID}'..."
gcloud builds submit . \
  --config=ci/cloudbuild.yaml \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --substitutions="_ENV=${ENV_NAME},_REGION=${REGION},_REPO=demo-apps,_APP_NAME=demo-api"
