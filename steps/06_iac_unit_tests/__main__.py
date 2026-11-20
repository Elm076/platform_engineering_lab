"""Step 6 entry point: delegates to infra.py so tests and deploys share the exact same code."""

from __future__ import annotations

import pulumi
from infra import create_app_infrastructure

stack = pulumi.get_stack()
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

resources = create_app_infrastructure(
    stack=stack,
    project_id=gcp_config.require("project"),
    region=gcp_config.get("region") or "europe-west4",
    manage_registry=config.get_bool("manage_registry") or False,
    greeting_value=config.get("greeting"),
    min_instances=config.get_int("min_instances") or 0,
    max_instances=config.get_int("max_instances") or 5,
)

pulumi.export("env", stack)
pulumi.export("bucket_name", resources.bucket.name)
pulumi.export("seed_file", resources.seed_file.name)
pulumi.export("greeting_secret_id", resources.greeting_secret.secret_id)
pulumi.export("service_url", resources.service.uri)
