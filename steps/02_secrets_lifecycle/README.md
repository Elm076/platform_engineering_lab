# Step 2 — IaC Lifecycle, Surgical Diffs & Idempotency

## Concept
Secret Manager secrets are fast, cheap, and ideal for demonstrating the core IaC workflow:
1. **Create**: add new resources while existing ones (`app-storage`) stay untouched.
2. **Idempotency**: running `pulumi up` twice with no code changes performs **0 operations**.
3. **Modify & Delete**: updating a label or removing a block touches *only* the affected resources.

## Live Stage Sequence

Update `Pulumi.yaml`:

```yaml
main: steps/02_secrets_lifecycle
```

1. **Add two secrets** (note `app-storage` and `app-storage-seed` remain unchanged):
   ```bash
   pulumi up
   ```
2. **Prove idempotency** — run it again immediately with no edits:
   ```bash
   pulumi up
   # Expected: 0 to create, 0 to update, 0 to delete
   ```
3. **Modify one secret + delete the other**:
   - In `steps/02_secrets_lifecycle/__main__.py`:
     - Change `labels={"revision": "v1"}` → `labels={"revision": "v2"}` on `app-greeting-secret`.
     - Comment out `feature_flag_secret` and `feature_flag_version`.
   - Run `pulumi preview` and `pulumi up` to see the surgical diff (`1 updated, 2 deleted, 4 unchanged`).
