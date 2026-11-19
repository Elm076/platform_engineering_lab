"""Step 5: Multi-Environment Delivery — prod + dev Stacks from One Codebase."""

from __future__ import annotations

import json

import pulumi
import pulumi_gcp as gcp

stack = pulumi.get_stack()
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west4"
manage_registry = config.get_bool("manage_registry") or False
greeting_value = config.get("greeting") or f"Hola DevFest Jaen 2026 ({stack})!"
min_instances = config.get_int("min_instances") or 0
max_instances = config.get_int("max_instances") or 3

# Every environment gets its own isolated bucket, seed file, secret, and Cloud Run service.
# Note: For this demo, dev and prod live in ONE GCP project using `-{stack}` suffixes.
# In real production setups, configure a SEPARATE `gcp:project` in Pulumi.dev.yaml vs Pulumi.prod.yaml!
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
            "event": "DevFest Jaen 2026",
        },
        indent=2,
    ),
)

greeting_secret = gcp.secretmanager.Secret(
    "app-greeting-secret",
    secret_id=f"demo-api-greeting-{stack}",
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
)

greeting_version = gcp.secretmanager.SecretVersion(
    "app-greeting-version",
    secret=greeting_secret.id,
    secret_data=greeting_value,
)

# Shared Artifact Registry: owned by `prod` (`manage_registry: true`), reused by `dev`.
# Compare this plain Python `if` with Terraform's `count = var.manage_registry ? 1 : 0`.
if manage_registry:
    gcp.artifactregistry.Repository(
        "app-registry",
        repository_id="demo-apps",
        location=region,
        format="DOCKER",
        description="Container images for DevFest Jaen 2026 platform demo",
    )

# Still using default Compute Engine SA — we fix this in Step 7 (DevSecOps).
default_sa = gcp.compute.get_default_service_account(project=project_id)
default_sa_secret_access = gcp.secretmanager.SecretIamMember(
    "app-default-sa-secret-access",
    secret_id=greeting_secret.id,
    role="roles/secretmanager.secretAccessor",
    member=f"serviceAccount:{default_sa.email}",
)

bootstrap_image = f"{region}-docker.pkg.dev/{project_id}/demo-apps/demo-api:v1"

service = gcp.cloudrunv2.Service(
    "app-service",
    name=f"demo-api-{stack}",
    location=region,
    ingress="INGRESS_TRAFFIC_ALL",
    deletion_protection=False,
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=min_instances,
            max_instance_count=max_instances,
        ),
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=bootstrap_image,
                envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="APP_NAME",
                        value="demo-api",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="APP_ENV",
                        value=stack,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="GCS_BUCKET_NAME",
                        value=bucket.name,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="APP_GREETING",
                        value_source=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceArgs(
                            secret_key_ref=gcp.cloudrunv2.ServiceTemplateContainerEnvValueSourceSecretKeyRefArgs(
                                secret=greeting_secret.secret_id,
                                version="latest",
                            ),
                        ),
                    ),
                ],
            )
        ],
    ),
    opts=pulumi.ResourceOptions(
        ignore_changes=["template.containers[0].image"],
        depends_on=[greeting_version, default_sa_secret_access],
    ),
)

invoker = gcp.cloudrunv2.ServiceIamMember(
    "app-service-invoker",
    name=service.name,
    location=region,
    role="roles/run.invoker",
    member="allUsers",
)

pulumi.export("env", stack)
pulumi.export("bucket_name", bucket.name)
pulumi.export("greeting_secret_id", greeting_secret.secret_id)
pulumi.export("service_url", service.uri)
