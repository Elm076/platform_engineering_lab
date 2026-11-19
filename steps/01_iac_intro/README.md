# Step 1 — First Steps with IaC (+ Python vs. HCL)

## Concept
Instead of clicking in the GCP Console, we declare our desired cloud state in **plain Python**:
- **Declarative graph**: referencing `bucket.name` inside `BucketObject` tells the IaC engine to create the bucket first, then upload `welcome.json`.
- **Preview before applying**: inspect every planned cloud change before anything is created.
- **Python vs. HCL**: compare `__main__.py` with [`comparison.tf`](comparison.tf) — developers can reuse Python types, `json.dumps`, IDE autocomplete, loops, classes, and `pytest` instead of learning a DSL from scratch.

## Commands

Ensure `Pulumi.yaml` has:

```yaml
main: steps/01_iac_intro
```

Then run:

```bash
pulumi stack select prod
pulumi preview
pulumi up
```
