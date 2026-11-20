"""Step 2: IaC lifecycle — Adding, modifying, deleting resources & idempotency."""

from __future__ import annotations

import json

import pulumi
import pulumi_gcp as gcp

stack = pulumi.get_stack()
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project_id = gcp_config.require("project")
greeting_value = config.get("greeting") or f"Hola DevFest Jaén 2026 ({stack})!"

# --- Existing Step 1 resources (untouched by our Secret Manager changes!) ---
bucket = gcp.storage.Bucket(
    "app-storage",
    name=f"{project_id}-demo-api-{stack}",
    location="EUROPE-WEST4",
    uniform_bucket_level_access=True,
    public_access_prevention="enforced",
    force_destroy=True,
)

seed_file = gcp.storage.BucketObject(
    "app-storage-seed",
    name="welcome.json",
    bucket=bucket.name,
    content_type="application/json",
    content=json.dumps(
        {
            "message": "Hello from Google Cloud Storage managed by IaC!",
            "env": stack,
            "event": "DevFest Jaén 2026",
        },
        indent=2,
    ),
)

# --- Step 2: Secret Manager resources for demonstrating CRUD & idempotency ---
greeting_secret = gcp.secretmanager.Secret(
    "app-greeting-secret",
    secret_id=f"demo-api-greeting-{stack}",
    # Live demo edit #1: change "v1" -> "v2" to see an in-place update!
    labels={"revision": "v1"},
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
)

greeting_version = gcp.secretmanager.SecretVersion(
    "app-greeting-version",
    secret=greeting_secret.id,
    secret_data=greeting_value,
)

# Live demo edit #2: comment out this second secret block and run `pulumi up`
# to show IaC cleanly deleting ONLY the removed resource!
feature_flag_secret = gcp.secretmanager.Secret(
    "app-feature-flag-secret",
    secret_id=f"demo-api-feature-flag-{stack}",
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
)

feature_flag_version = gcp.secretmanager.SecretVersion(
    "app-feature-flag-version",
    secret=feature_flag_secret.id,
    secret_data="beta-enabled",
)

pulumi.export("bucket_name", bucket.name)
pulumi.export("seed_file", seed_file.name)
pulumi.export("greeting_secret_id", greeting_secret.secret_id)
