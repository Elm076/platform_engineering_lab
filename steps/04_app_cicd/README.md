# Step 4 — Early Automation: App CI/CD with Cloud Build + FastAPI Unit Tests

## Concept
Before automating infrastructure deployments, most teams first automate **application delivery**:
- **Shift-left testing**: run `pytest` unit tests (with mocked GCS calls) before building a Docker image.
- **Reproducible builds**: Cloud Build builds and pushes an immutable `:${BUILD_ID}` container image to Artifact Registry.
- **Safe rollout**: Cloud Build updates *only* the Cloud Run container image while preserving IaC-managed env vars, secrets, and IAM.

*(No changes to `Pulumi.yaml` in this step — we stay on `steps/03_import_clickops` to show app CI/CD evolving independently from IaC.)*

## Files Highlighted on Stage
- [`app/tests/test_main.py`](../../app/tests/test_main.py) — FastAPI `TestClient` + mocked GCS
- [`ci/cloudbuild.yaml`](../../ci/cloudbuild.yaml) — 4-step pipeline (`unit-tests` → `build-image` → `push-image` → `deploy-cloud-run`)
- [`scripts/deploy_app.sh`](../../scripts/deploy_app.sh) — manual/CLI trigger wrapper (zero GitHub OAuth friction)

## Live Stage Commands

1. Run the FastAPI unit tests locally (<1s):
   ```bash
   .venv/bin/pytest -v app/tests/
   ```
2. Trigger the Cloud Build pipeline for `prod`:
   ```bash
   ./scripts/deploy_app.sh prod "$GCP_PROJECT"
   ```
   *(Tip on stage: kick off `./scripts/deploy_app.sh prod` first and walk through `app/tests/test_main.py` and `ci/cloudbuild.yaml` while Cloud Build runs!)*
3. Verify the deployed service is healthy:
   ```bash
   PROD_URL=$(pulumi stack output service_url)
   curl -s "${PROD_URL}/health" | python3 -m json.tool
   ```

> **Optional live failure demo:** Break an assertion in `app/tests/test_main.py` (or change `/health` status) and show how `pytest` stops the pipeline before Docker even starts building.
