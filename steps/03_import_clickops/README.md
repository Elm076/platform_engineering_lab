# Step 3 — Brownfield adoption: Importing clickOps resources into IaC

## Concept

Real teams rarely start from a blank cloud project. Instead of recreating production from scratch, IaC lets you **import** existing clickOps resources into the state and then evolve them safely:

1. Import the Artifact Registry repository (`demo-apps`) and Cloud Run service (`demo-api-prod`).
2. Wire our IaC-managed GCS bucket and Secret Manager secret into Cloud Run's environment variables.
3. Separate responsibilities cleanly using `ignore_changes=["template.containers[0].image"]` so our upcoming CI/CD pipeline can roll out new app builds without IaC reverting them.

## Live stage sequence

1. Import both clickOps resources into the `prod` stack (before switching `Pulumi.yaml` or right after):

   ```bash
   pulumi stack select prod

   pulumi import gcp:artifactregistry/repository:Repository app-registry \
     "projects/${GCP_PROJECT}/locations/europe-west4/repositories/demo-apps" \
     --yes

   pulumi import gcp:cloudrunv2/service:Service app-service \
     "projects/${GCP_PROJECT}/locations/europe-west4/services/demo-api-prod" \
     --yes
   ```

   *(Tip: Pulumi even prints generated Python code during `pulumi import`, showing how developers can reverse-engineer clickOps!)*

2. Point `Pulumi.yaml` to Step 3:

   ```yaml
   main: steps/03_import_clickops
   ```

3. Apply the wiring (GCS bucket + Secret Manager greeting injected into Cloud Run):

   ```bash
   pulumi preview
   pulumi up
   ```

4. Verify live — `/` now serves the greeting from Secret Manager, and `/storage` lists `welcome.json` as JSON:

   ```bash
   PROD_URL=$(pulumi stack output service_url)
   curl -s "${PROD_URL}/" | python3 -m json.tool
   curl -s "${PROD_URL}/storage" | python3 -m json.tool
   ```
