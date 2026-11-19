# Local & Google Cloud Setup Guide

Follow these steps to run this demo on your own Google Cloud project (either before presenting or when exploring the repo after the talk).

> **Cost note:** Every resource in this demo is serverless / scale-to-zero (Cloud Run v2, GCS, Secret Manager, IAM, Cloud Monitoring) and fits well within Google Cloud free tiers or pennies during a short session. Always run `./scripts/cleanup.sh` when you finish.

---

## 1. Prerequisites

Install the following tools:

- **Python 3.11 – 3.13** (`python3 --version`)
- **Google Cloud CLI (`gcloud`)**: [Install guide](https://cloud.google.com/sdk/docs/install)
- **Pulumi CLI**: [Install guide](https://www.pulumi.com/docs/iac/download-install/)
  ```bash
  curl -fsSL https://get.pulumi.com | sh
  ```

---

## 2. Select or Create a Google Cloud Project

1. Authenticate your `gcloud` CLI and Application Default Credentials (ADC — required by Pulumi's GCP provider):
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
2. List your existing projects or create a dedicated sandbox project:
   ```bash
   gcloud projects list
   # Optional: create a new project
   # gcloud projects create my-devfest-demo --name="DevFest Jaen Demo"
   ```
3. Make sure **Billing** is enabled on the project (required for Cloud Run, Artifact Registry, Cloud Build, and Secret Manager).
4. Set your active project and default region (`europe-west4`):
   ```bash
   export GCP_PROJECT="YOUR_GCP_PROJECT_ID"
   gcloud config set project "$GCP_PROJECT"
   gcloud config set run/region europe-west4
   gcloud auth application-default set-quota-project "$GCP_PROJECT"
   ```

---

## 3. Set Up the Python Virtual Environment

From the root of this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Verify the FastAPI tests run locally:

```bash
.venv/bin/pytest app/tests/
```

---

## 4. Configure Pulumi (Local State Backend)

For maximum reliability on conference Wi-Fi (no external SaaS dependency), this demo uses Pulumi's **local state backend**:

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

*(You will initialize the `dev` stack later in Step 5.)*

---

## 5. Pre-Provision Step 0 ("ClickOps Baseline")

Before walking through Steps 1–9, run the pre-talk baseline script. It enables the required GCP APIs, creates the `demo-apps` Artifact Registry repo, builds & pushes the initial FastAPI container image (`:v1`), and deploys `demo-api-prod` to Cloud Run (simulating an app originally deployed via ClickOps):

```bash
./scripts/setup_clickops.sh "$GCP_PROJECT"
```

---

## 6. How to Advance Between Steps

Every step lives in its own folder under `steps/` so you can browse or edit each step independently while keeping **one continuous Pulumi state**.

To move to the next step, update the single `main:` line in `Pulumi.yaml`:

```yaml
main: steps/01_iac_intro
```

Then run `pulumi preview` and `pulumi up` from the repository root.

---

## 7. Full Teardown (Cleanup)

When you are done, remove all demo resources cleanly:

```bash
./scripts/cleanup.sh "$GCP_PROJECT"
```
