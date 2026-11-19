"""Step 1: Introduction to IaC in Python — GCS Bucket + Initial Seed File."""

from __future__ import annotations

import json

import pulumi
import pulumi_gcp as gcp

stack = pulumi.get_stack()
gcp_config = pulumi.Config("gcp")
project_id = gcp_config.require("project")

# 1. Provision a private Cloud Storage bucket for the application.
bucket = gcp.storage.Bucket(
    "app-storage",
    name=f"{project_id}-demo-api-{stack}",
    location="EUROPE-WEST4",
    uniform_bucket_level_access=True,
    public_access_prevention="enforced",
    force_destroy=True,  # Demo convenience: allows clean teardown even with objects inside.
)

# 2. Upload an initial JSON seed file so the app's /storage endpoint has data to list.
#    Passing `bucket=bucket.name` automatically builds a dependency in the IaC graph.
seed_file = gcp.storage.BucketObject(
    "app-storage-seed",
    name="welcome.json",
    bucket=bucket.name,
    content_type="application/json",
    content=json.dumps(
        {
            "message": "Hello from Google Cloud Storage managed by IaC!",
            "env": stack,
            "event": "DevFest Jaen 2026",
        },
        indent=2,
    ),
)

pulumi.export("bucket_name", bucket.name)
pulumi.export("seed_file", seed_file.name)
