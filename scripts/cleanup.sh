#!/usr/bin/env bash
# Clean teardown of Pulumi stacks (dev first, then prod) and any remaining Step 0 ClickOps resources.
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-europe-west4}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Usage: $0 <GCP_PROJECT_ID> [REGION]"
  exit 1
fi

export PULUMI_CONFIG_PASSPHRASE="${PULUMI_CONFIG_PASSPHRASE:-}"

# Destroy dev before prod so prod's shared Artifact Registry repo is removed last.
if command -v pulumi >/dev/null 2>&1; then
  for STACK in dev prod; do
    if pulumi stack select "${STACK}" >/dev/null 2>&1; then
      echo "==> Destroying Pulumi stack '${STACK}'..."
      pulumi destroy --yes || true
    fi
  done
fi

echo "==> Ensuring Step 0 ClickOps resources are removed if not managed by Pulumi..."
gcloud run services delete demo-api-prod \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet 2>/dev/null || true

gcloud artifacts repositories delete demo-apps \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet 2>/dev/null || true

echo "==> Cleanup complete for project '${PROJECT_ID}'."
