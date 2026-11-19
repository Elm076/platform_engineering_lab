# Step 5 — Multi-Environment Delivery (`dev` + `prod` Stacks & 2 CI/CD Pipelines)

## Concept
Shipping directly to `prod` is risky. With IaC **Stacks**, we reuse the **exact same Python code** with separate state files and per-environment config (`Pulumi.dev.yaml` vs. `Pulumi.prod.yaml`) to spin up an isolated `dev` environment in seconds.

> **Real-world architecture callout:** For demo simplicity, both `dev` and `prod` live in the **same GCP project** using `-{stack}` resource name suffixes. In production, each stack sets a **different `gcp:project`** in `Pulumi.<stack>.yaml` for hard IAM, quota, and billing isolation (and shared services like Artifact Registry often live in a dedicated `shared` project).

## Live Stage Commands

1. Point `Pulumi.yaml` to Step 5:
   ```yaml
   main: steps/05_multi_env
   ```

2. Create and deploy the brand-new **`dev`** environment from the same codebase:
   ```bash
   pulumi stack init dev
   pulumi config set gcp:project "$GCP_PROJECT"
   pulumi up
   ```

3. Verify `dev` is live and isolated from `prod`:
   ```bash
   DEV_URL=$(pulumi stack output service_url)
   curl -s "${DEV_URL}/" | python3 -m json.tool
   curl -s "${DEV_URL}/storage" | python3 -m json.tool
   ```

4. Show **two separate CI/CD targets** (`dev` vs. `prod`) using the same parameterized Cloud Build pipeline (in production, bound to `dev` and `main` Git branch triggers):
   ```bash
   ./scripts/deploy_app.sh dev "$GCP_PROJECT"
   # And after validating in dev, promote to prod:
   # ./scripts/deploy_app.sh prod "$GCP_PROJECT"
   ```

> **Pacing tip for Steps 7–9:** Stay on the `dev` stack for the remaining live deploys on stage (mirroring a real dev-first workflow), then mention promoting to `prod` via `pulumi stack select prod && pulumi up`.
