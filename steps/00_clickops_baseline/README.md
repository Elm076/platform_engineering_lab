# Step 0 — The clickOps baseline ("where every dev starts")

## Concept

Before adopting Platform Engineering or IaC, most teams ship their first cloud service by clicking through the cloud console (**clickOps**). It works quickly on day 1, but:

- There is no version history or code review of your infrastructure.
- Reproducing the exact setup for a `dev` environment or a second app is slow and error-prone.
- Defaults (such as running Cloud Run as the broad default Compute Engine Service Account) quietly accumulate security and cost risks.

## Pre-talk setup (simulating clickOps)

*(Check [`SETUP.md`](../../SETUP.md) before.)*

Run the repeatable baseline script before stepping on stage:

```bash
./scripts/setup_clickops.sh "$GCP_PROJECT"
```

This creates:

1. Artifact Registry Docker repository `demo-apps` (`europe-west4`)
1. Initial FastAPI container image `demo-api:v1`
1. Cloud Run service `demo-api-prod` (`--allow-unauthenticated`)

## Live stage sequence

```bash
export PROD_URL=$(gcloud run services describe demo-api-prod \
  --region=europe-west4 \
  --format='value(status.url)')

curl -s "${PROD_URL}/" | python3 -m json.tool
curl -s "${PROD_URL}/health" | python3 -m json.tool
curl -s "${PROD_URL}/storage" | python3 -m json.tool
```

Notice `/storage` currently returns `{"storage": "disabled", ...}` — we have not provisioned any storage or secrets yet.
