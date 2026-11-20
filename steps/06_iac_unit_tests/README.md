# Step 6 — Testing IaC like application code (`pytest` + mocks)

## Concept

Because our IaC is written in Python, developers can immediately bring **unit testing** also to cloud architecture! Using Pulumi's in-memory mocks, `pytest` validates security and scaling invariants **locally in <1 second without touching GCP or spending a cent**.

`steps/06_iac_unit_tests/infra.py` intentionally contains **two realistic bugs**:

1. **BUG 1 (Security):** The GCS bucket leaves `public_access_prevention="inherited"` and `uniform_bucket_level_access=False`.
2. **BUG 2 (Availability):** A copy-paste mistake caps `prod` Cloud Run at `max_instance_count=1`.

## Live stage sequence

1. Run the infrastructure unit tests **before** deploying anything:

   ```bash
   pytest -v steps/06_iac_unit_tests/tests/
   ```

   Watch **2 tests fail immediately in RED** (`test_bucket_enforces_private_access` and `test_prod_cloud_run_scaling_avoids_bottleneck`) while `test_cloud_run_wires_storage_and_secret` passes.

2. Fix both bugs in `steps/06_iac_unit_tests/infra.py`:
   - Set `uniform_bucket_level_access=True` and `public_access_prevention="enforced"`.
   - Set `effective_max_instances = max_instances`.

3. Re-run `pytest`:

   ```bash
   pytest -v steps/06_iac_unit_tests/tests/
   ```

   All **3 tests pass in GREEN** — without making a single cloud API call!

*(Optional: you can skip running `pulumi up` in this step since the fixed infra matches step 5, and move straight to step 7.)*
