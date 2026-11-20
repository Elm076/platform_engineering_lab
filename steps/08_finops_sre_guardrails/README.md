# Step 8 — finOps + SRE observability + Policy-as-Code guardrails

## Concept

Platform Engineering goes beyond spinning up servers — it embeds **cost governance**, **compliance**, and **observability** by default:

1. **finOps in IaC**: mandatory cost-attribution labels (`env`, `team`, `cost-center`, `managed-by`), Cloud Run CPU/memory ceilings with `cpu_idle=True`, scale-to-zero in `dev`, and a 30-day GCS lifecycle auto-delete rule in `dev`.
1. **SRE observability**: a `gcp.monitoring.AlertPolicy` watching Cloud Run `container/instance_count` spikes (connecting finOps cost anomalies with ops alerting).
1. **Policy-as-Code (`policy/`)**: a ~45-line Python CrossGuard policy pack enforcing finOps labels, approved EU regions (`europe-west4`), Cloud Run `max_instance_count <= 10`, `dev` scale-to-zero, and private GCS buckets — **blocking bad deployments before a single cent is spent**.

## Live stage sequence

Update `Pulumi.yaml`:

```yaml
main: steps/08_finops_sre_guardrails
```

1. **Guardrail failure demo**: temporarily set `max_instance_count=50` (or change `location="us-central1"`) in `steps/08_finops_sre_guardrails/__main__.py`, then run:

   ```bash
   pulumi preview --policy-pack policy
   ```

   Watch the Python Policy Pack **block the deployment red-handed**!

2. **Revert & apply cleanly**:

   ```bash
   pulumi up --policy-pack policy
   ```

   All 4 policies pass, labels & caps apply, and the Cloud Monitoring AlertPolicy is live in the GCP Console.
