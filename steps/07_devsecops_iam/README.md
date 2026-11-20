# Step 7 — DevSecOps: Least-privilege identity & resource-scoped IAM

## Concept

Until now, our Cloud Run service has been running as the **default Compute Engine Service Account** — an identity shared across the whole project and often granted overly broad roles like `roles/editor`.

With **devSecOps in IaC**, we bake least-privilege security right into the stack:

1. Create a dedicated Service Account per app & environment (`demo-api-{stack}-sa`).
2. Grant **only** `roles/secretmanager.secretAccessor` scoped to this app's single secret.
3. Grant **only** `roles/storage.objectViewer` scoped to this app's single bucket (since `/storage` only lists objects).
4. Notice `pulumi preview` also cleanly **removes** the temporary `app-default-sa-secret-access` binding from Step 3!

## Live stage sequence

Update `Pulumi.yaml`:

```yaml
main: steps/07_devsecops_iam
```

Apply on `dev` (and later promote to `prod`):

```bash
pulumi stack select dev
pulumi preview
pulumi up
```

Verify both Secret Manager and GCS still work under the locked-down Service Account:

```bash
DEV_URL=$(pulumi stack output service_url)
curl -s "${DEV_URL}/" | python3 -m json.tool
curl -s "${DEV_URL}/storage" | python3 -m json.tool
```
