# Step 8 — FinOps + SRE Observability + Policy-as-Code Guardrails

## Concept
Platform Engineering goes beyond spinning up servers — it embeds **cost governance**, **compliance**, and **observability** by default:
1. **FinOps in IaC**: mandatory cost-attribution labels (`env`, `team`, `cost-center`, `managed-by`), Cloud Run CPU/memory ceilings with `cpu_idle=True`, scale-to-zero in `dev`, and a 30-day GCS lifecycle auto-delete rule in `dev`.
2. **SRE Observability**: a `gcp.monitoring.AlertPolicy` watching Cloud Run `container/instance_count` spikes (connecting FinOps cost anomalies with Ops alerting).
3. **Policy-as-Code (`policy/`)**: a ~45-line Python CrossGuard policy pack enforcing FinOps labels, approved EU regions (`europe-west4`), Cloud Run `max_instance_count <= 10`, `dev` scale-to-zero, and private GCS buckets — **blocking bad deployments before a single cent is spent**.

## Live Stage Sequence

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
