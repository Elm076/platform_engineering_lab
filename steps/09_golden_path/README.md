# Step 9 — The platform engineering payoff: A reusable golden path

## Concept

Everything we built in steps 1–8 was for **one** app. Platform Engineering asks: *"How do we make the right way the easiest way for the next 20 apps?"*

By wrapping our security, finOps, and SRE best practices into a Python **`PlatformService` (`ComponentResource`)** with a typed `PlatformServiceArgs` contract:

1. **Zero-downtime refactoring**: `demo-api` (App #1) moves inside `PlatformService` using Pulumi `aliases` (`migrate_from_root=True`) — **0 replacements, 0 downtime**!
1. **Customizable paved road**: onboarding **`catalog-api` (App #2)** takes ~10 readable lines of Python while tailoring values to its needs:
   - `enable_storage=False` (stateless service — no GCS bucket or storage IAM provisioned)
   - Different `team="catalog"` and `cost_center="cc-202"`
   - Custom `max_instances=4` and app-specific `extra_env={"CUSTOM_MODE": "catalog-v2", "CUSTOM_TIER": "gold"}`
1. Every app onboarded via `PlatformService` automatically inherits least-privilege IAM, Secret Manager, Cloud Monitoring alerting, and passes our `--policy-pack policy` guardrails!

## Live stage sequence

Update `Pulumi.yaml`:

```yaml
main: steps/09_golden_path
```

Preview and deploy with the Policy Pack still enforced:

```bash
pulumi preview --policy-pack policy
pulumi up --policy-pack policy
```

Compare both live JSON APIs side by side:

```bash
DEMO_URL=$(pulumi stack output demo_api_url)
CATALOG_URL=$(pulumi stack output catalog_api_url)

# App #1 (storage enabled, platform team)
curl -s "${DEMO_URL}/" | python3 -m json.tool
curl -s "${DEMO_URL}/storage" | python3 -m json.tool

# App #2 (stateless, custom env vars, catalog team)
curl -s "${CATALOG_URL}/" | python3 -m json.tool
curl -s "${CATALOG_URL}/storage" | python3 -m json.tool
```

## Where teams go next in production

- **Remote IaC state**: GCS bucket (`pulumi login gs://...`) or Pulumi Cloud with state locking.
- **Hard environment isolation**: separate GCP projects per stack (`Pulumi.dev.yaml` vs. `Pulumi.prod.yaml`).
- **IaC CI/CD**: run `pytest` + `pulumi preview --policy-pack policy` automatically on every PR.
- **Internal developer portal**: expose `PlatformService` via a YAML catalog, Backstage template, or Pulumi Automation API.
