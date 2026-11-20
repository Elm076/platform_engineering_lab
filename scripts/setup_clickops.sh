#!/usr/bin/env bash
# Pre-talk helper: provisions step 0 ("clickOps baseline") reproducibly before going on stage.
# During the talk, this represents an app that a developer originally deployed via clickOps.
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-europe-west4}"
REPO_NAME="demo-apps"
APP_NAME="demo-api"
SERVICE_NAME="${APP_NAME}-prod"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> [REGION]"
  echo "Or set a default project first: gcloud config set project <GCP_PROJECT_ID>"
  exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${APP_NAME}:v1"
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo "==> Target project: ${PROJECT_ID} (number: ${PROJECT_NUMBER}), region: ${REGION}"

echo "==> 1/5 Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  monitoring.googleapis.com \
  iam.googleapis.com \
  compute.googleapis.com \
  --project="${PROJECT_ID}"

echo "==> 2/5 Ensuring Cloud Build has permissions to deploy to Cloud Run & push images..."
# Newer GCP projects execute Cloud Build using the default Compute Engine SA;
# older projects use the legacy Cloud Build SA. Grant both to avoid live demo surprises.
for SA in \
  "${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; do
  for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${SA}" \
      --role="${ROLE}" \
      --quiet >/dev/null || true
  done
done

echo "==> 3/5 Creating Artifact Registry repository '${REPO_NAME}' (if missing)..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Container images for DevFest Jaén 2026 platform demo" \
    --project="${PROJECT_ID}"
else
  echo "    Repository '${REPO_NAME}' already exists, skipping."
fi

echo "==> 4/5 Building & pushing initial FastAPI image (${IMAGE_URI})..."
gcloud builds submit app \
  --tag="${IMAGE_URI}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}"

echo "==> 5/5 Deploying initial clickOps Cloud Run service '${SERVICE_NAME}'..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_URI}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --set-env-vars="APP_NAME=${APP_NAME},APP_ENV=prod" \
  --quiet

PROD_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')"

echo ""
echo "=================================================================="
echo "Step 0 (clickOps baseline) is ready!"
echo "Service URL: ${PROD_URL}"
echo ""
echo "Try:"
echo "  export PROD_URL=\"${PROD_URL}\""
echo "  curl -s \"\${PROD_URL}/\" | python3 -m json.tool"
echo "  curl -s \"\${PROD_URL}/health\" | python3 -m json.tool"
echo "  curl -s \"\${PROD_URL}/storage\" | python3 -m json.tool"
echo "=================================================================="
