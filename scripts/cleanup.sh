#!/usr/bin/env bash
# Full demo teardown & repository reset so the repo is ready to deliver the demo again.
#
# Usage:
#   ./scripts/cleanup.sh [GCP_PROJECT_ID] [REGION]
#   (GCP_PROJECT_ID defaults to `gcloud config get-value project`; REGION defaults to europe-west4.)
#
# What this script reverts:
#   1. Destroys all resources in Pulumi stacks `dev` and `prod` (dev first so prod's shared
#      Artifact Registry is removed last) and removes both stacks with `--preserve-config`
#      so `Pulumi.dev.yaml` and `Pulumi.prod.yaml` are NOT deleted from disk.
#   2. Removes any remaining step 0 clickOps resources created by `scripts/setup_clickops.sh`:
#      - Step 5/5: Cloud Run service `demo-api-prod`
#      - Step 3/5 & 4/5: Artifact Registry repo `demo-apps` (and all container images inside it)
#   3. Restores all Python files modified across steps 0-9 (`steps/`, `app/`, `policy/`),
#      `ci/`, and Pulumi YAML files (`Pulumi.yaml` back to `steps/01_iac_intro`, plus clean
#      `Pulumi.prod.yaml` and `Pulumi.dev.yaml`) to `HEAD`, preserving `.venv/`.
#      NOTE: Uses `git checkout HEAD -- Pulumi.yaml Pulumi.prod.yaml Pulumi.dev.yaml steps app policy ci`
#      and `git clean -fd -- steps app policy ci`, which discards ANY uncommitted edits or
#      untracked files in those paths—not only edits made while following steps 0-9.
#
# Steps from `scripts/setup_clickops.sh` intentionally NOT reverted (and do not need to be):
#   - Step 1/5 (Enabling GCP APIs: run, artifactregistry, secretmanager, cloudbuild, monitoring,
#     iam, compute): idempotent, free when no resources are running, and disabling them could
#     disrupt other workloads or cause re-enablement delays on the next demo run.
#   - Step 2/5 (Cloud Build IAM bindings on the Cloud Build & default Compute Engine SAs):
#     idempotent, free, and removing them could break other Cloud Build pipelines in the project.
#   - Step 4/5 side-effects (Cloud Build build history & default Cloud Build staging bucket):
#     shared project-level build artifacts that are safe to leave in place (the container images
#     themselves ARE deleted along with the `demo-apps` Artifact Registry repository).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-europe-west4}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Usage: $0 [GCP_PROJECT_ID] [REGION]"
  echo "Or set a default project first: gcloud config set project <GCP_PROJECT_ID>"
  exit 1
fi

if ! command -v pulumi >/dev/null 2>&1 && [[ -x "${HOME}/.pulumi/bin/pulumi" ]]; then
  export PATH="${HOME}/.pulumi/bin:${PATH}"
fi

export PULUMI_CONFIG_PASSPHRASE="${PULUMI_CONFIG_PASSPHRASE:-}"

echo "==> Target project: ${PROJECT_ID}, region: ${REGION}"

# 1. Destroy & remove Pulumi stacks (dev before prod so prod's shared Artifact Registry is removed last).
#    `--preserve-config` deletes the stack from Pulumi state WITHOUT deleting Pulumi.<stack>.yaml.
echo "==> 1/3 Tearing down Pulumi stacks (preserving Pulumi.*.yaml)..."
if command -v pulumi >/dev/null 2>&1; then
  for STACK in dev prod; do
    if pulumi stack select "${STACK}" >/dev/null 2>&1; then
      echo "    Destroying resources in Pulumi stack '${STACK}'..."
      if pulumi destroy --yes; then
        echo "    Deleting Pulumi stack '${STACK}' (keeping Pulumi.${STACK}.yaml)..."
        pulumi stack rm "${STACK}" --yes --preserve-config
      else
        echo "    WARNING: 'pulumi destroy' failed for stack '${STACK}'; skipping 'pulumi stack rm' so live GCP resources are not orphaned." >&2
      fi
    else
      echo "    Pulumi stack '${STACK}' not found; skipping."
    fi
  done
else
  echo "    WARNING: 'pulumi' CLI not found in PATH; skipping Pulumi stack teardown." >&2
fi

# 2. Fallback cleanup for step 0 clickOps resources if not yet managed by Pulumi.
echo "==> 2/3 Ensuring step 0 clickOps resources (setup_clickops.sh steps 3/5, 4/5 images, 5/5) are removed..."
if gcloud run services describe demo-api-prod \
  --region="${REGION}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "    Deleting Cloud Run service 'demo-api-prod'..."
  gcloud run services delete demo-api-prod \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet
else
  echo "    Cloud Run service 'demo-api-prod' already absent."
fi

if gcloud artifacts repositories describe demo-apps \
  --location="${REGION}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "    Deleting Artifact Registry repository 'demo-apps' (and its container images)..."
  gcloud artifacts repositories delete demo-apps \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet
else
  echo "    Artifact Registry repository 'demo-apps' already absent."
fi

# 3. Restore demo Python files & Pulumi YAML files back to initial (step 0) repo state.
echo "==> 3/3 Restoring repository files to initial (step 0) state..."
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  # Revert any live edits made across steps 0-9 (Python files in steps/, app/, policy/,
  # ci/cloudbuild.yaml, Pulumi.yaml `main:` pointer, and stack-specific config written
  # to Pulumi.prod.yaml / Pulumi.dev.yaml) without removing .venv/ or the YAML files.
  git checkout HEAD -- \
    Pulumi.yaml \
    Pulumi.prod.yaml \
    Pulumi.dev.yaml \
    steps \
    app \
    policy \
    ci

  # Remove any stray untracked files created inside demo directories during a run.
  git clean -fd -- steps app policy ci

  # Remove repo-local .pulumi/ state folder if present (does not touch ~/.pulumi/ or .venv/).
  if [[ -d "${REPO_ROOT}/.pulumi" ]]; then
    rm -rf "${REPO_ROOT}/.pulumi"
  fi

  REMAINING_STATUS="$(git status --short)"
  if [[ -z "${REMAINING_STATUS}" ]]; then
    echo "    Git working tree is clean and ready for the next demo run."
  else
    echo "    Demo files restored. Remaining local changes outside demo paths:"
    printf '%s\n' "${REMAINING_STATUS}" | sed 's/^/      /'
  fi
else
  echo "    WARNING: Not inside a git working tree; skipping automatic file restore." >&2
  echo "    Manually ensure Pulumi.yaml points to 'steps/01_iac_intro' and revert any step 2/4/6/8 edits." >&2
fi

echo ""
echo "=================================================================="
echo "Cleanup complete for project '${PROJECT_ID}'!"
echo ""
echo "Setup steps from scripts/setup_clickops.sh intentionally NOT reverted"
echo "(idempotent, free when idle, and safe to keep for the next demo):"
echo "  - Step 1/5: Enabled GCP APIs (run, artifactregistry, secretmanager,"
echo "              cloudbuild, monitoring, iam, compute)"
echo "  - Step 2/5: Cloud Build IAM bindings (Cloud Build & default Compute SAs)"
echo "  - Step 4/5: Cloud Build build history & default Cloud Build staging bucket"
echo "              (container images were deleted with the 'demo-apps' repo)"
echo ""
echo "Local Python virtualenv (.venv/) was also preserved."
echo ""
echo "Ready to deliver the demo again:"
echo "  1. export PULUMI_CONFIG_PASSPHRASE=\"\""
echo "  2. pulumi stack init prod && pulumi config set gcp:project \"${PROJECT_ID}\""
echo "  3. ./scripts/setup_clickops.sh"
echo "=================================================================="
