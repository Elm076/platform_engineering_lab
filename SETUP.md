# Local & Google Cloud setup guide

Follow these steps to run this demo on your own Google Cloud project (either before presenting or when exploring the repo after the talk).

> **Cost note:** Every resource in this demo is serverless / scale-to-zero (Cloud Run v2, GCS, Secret Manager, IAM, Cloud Monitoring) and fits well within Google Cloud free tiers or pennies during a short session. Always run `./scripts/cleanup.sh` when you finish.

---

## 1. Prerequisites

Install the following tools:

- **Python 3.11 – 3.14** (`python --version`; tested on 3.14 — FastAPI requires ≥ 3.11)
- **Google Cloud CLI (`gcloud`)**: [Install guide](https://cloud.google.com/sdk/docs/install)
- **Pulumi CLI ≥ 3.130** (`pulumi version`; **≥ 3.272** if using Python 3.14, tested on 3.277): [Install guide](https://www.pulumi.com/docs/iac/download-install/)

  ```bash
  curl -fsSL https://get.pulumi.com | sh
  ```

---

## 2. Select or create a Google Cloud project

1. Authenticate your `gcloud` CLI and Application Default Credentials (ADC — required by Pulumi's GCP provider):

   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. List your existing projects or create a dedicated sandbox project:

   ```bash
   gcloud projects list
   # Optional: create a new project with a globally unique ID
   # gcloud projects create my-devfest-demo --name="DevFest Jaen Demo"
   ```

3. Make sure **Billing** is enabled on the project (required for Cloud Run, Artifact Registry, Cloud Build, and Secret Manager).
4. Set your active project and default region (e.g. `europe-west4`):

   ```bash
   export GCP_PROJECT="YOUR_GCP_PROJECT_ID"
   gcloud config set project "$GCP_PROJECT"
   gcloud config set run/region europe-west4
   gcloud auth application-default set-quota-project "$GCP_PROJECT"
   ```

---

## 3. Set up the Python virtual env

From the root of this repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify the FastAPI tests run locally:

```bash
pytest app/tests/
```

---

## 4. Configure Pulumi (local state backend)

For maximum reliability on conference wifi, this demo uses Pulumi's **local state backend** instead of Pulumi Cloud or a remote backend:

```bash
pulumi login --local
```

> **Production note:** Real platform teams store IaC state in a **remote backend** (such as Pulumi Cloud or a GCS bucket via `pulumi login gs://my-state-bucket`) so teammates share state safely with locking and audit history.

Initialize the `prod` stack and bind it to your GCP project:

```bash
export PULUMI_CONFIG_PASSPHRASE=""   # Local demo convenience only; use KMS/secrets in prod
pulumi stack init prod
pulumi config set gcp:project "$GCP_PROJECT"
```

*(You will initialize the `dev` stack later in step 5.)*

---

## 5. Pre-provision step 0 ("clickOps")

Before walking through steps 1–9, run the pre-talk pre-provisioning script. It enables the required GCP APIs in your project, creates the `demo-apps` Artifact Registry repo, builds & pushes the initial FastAPI container image (`:v1`), and deploys `demo-api-prod` to Cloud Run (simulating an app originally deployed via clickOps):

```bash
./scripts/setup_clickops.sh
# Optional: pass project ID (and region, default: europe-west4) explicitly
# ./scripts/setup_clickops.sh ["$GCP_PROJECT"] [REGION]
```

> **Note:** `"$GCP_PROJECT"` is optional — you can omit it if you already configured your default project with `gcloud config set project` in step 2.

---

## 6. How to advance between steps

Every step lives in its own folder under `steps/` so you can browse or edit each step independently while keeping **one continuous Pulumi state**.

To move to the next step, update the single `main:` line in `Pulumi.yaml`:

```yaml
main: steps/01_iac_intro
```

Then run `pulumi preview` and `pulumi up` from the repository root.

---

## 7. Full teardown (cleanup)

When you are done (or want to reset your environment and repository to deliver the demo again from step 0), run:

```bash
./scripts/cleanup.sh
# Optional: pass project ID (and region, default: europe-west4) explicitly
# ./scripts/cleanup.sh ["$GCP_PROJECT"] [REGION]
```

> **Note:** `"$GCP_PROJECT"` is optional if you already configured your default project with `gcloud config set project` in step 2.

`scripts/cleanup.sh` will:

1. Destroy all cloud resources in the `dev` and `prod` Pulumi stacks and delete both stacks while preserving `Pulumi.dev.yaml` and `Pulumi.prod.yaml` (`--preserve-config`).
2. Delete any remaining step 0 clickOps resources (`demo-api-prod` Cloud Run service and `demo-apps` Artifact Registry repository + container images).
3. Restore all Python files modified across steps 0–9 (`steps/`, `app/`, `policy/`), `ci/`, and Pulumi YAML files (`Pulumi.yaml` back to `steps/01_iac_intro`, plus clean `Pulumi.prod.yaml` and `Pulumi.dev.yaml`) to the initial repository state (preserving `.venv/`).

> **Note:** Step 3 runs `git checkout HEAD -- Pulumi.yaml Pulumi.prod.yaml Pulumi.dev.yaml steps app policy ci` and `git clean -fd -- steps app policy ci`. This will discard **any** uncommitted edits or untracked files you made in those paths—not only changes made while following steps 0–9. Commit or stash your changes first if you want to keep them.

Project-level prerequisites from `scripts/setup_clickops.sh` (enabled GCP APIs, Cloud Build IAM bindings, and Cloud Build history/staging bucket) are intentionally left intact since they are free when idle and idempotent on subsequent runs.
