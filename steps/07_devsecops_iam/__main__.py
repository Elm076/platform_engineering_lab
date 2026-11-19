"""Step 7: DevSecOps — Dedicated Least-Privilege Service Account & Resource-Scoped IAM."""

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

# --- Core storage & secret resources ---
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

if manage_registry:
    gcp.artifactregistry.Repository(
        "app-registry",
        repository_id="demo-apps",
        location=region,
        format="DOCKER",
        description="Container images for DevFest Jaen 2026 platform demo",
    )

# --- Step 7 (DevSecOps): Dedicated least-privilege identity per app & environment ---
app_sa = gcp.serviceaccount.Account(
    "app-sa",
    account_id=f"demo-api-{stack}-sa",
    display_name=f"Least-privilege runtime SA for demo-api ({stack})",
)

# Grant read access ONLY to this app's secret (never project-wide!)
secret_accessor = gcp.secretmanager.SecretIamMember(
    "app-secret-accessor",
    secret_id=greeting_secret.id,
    role="roles/secretmanager.secretAccessor",
    member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

# Grant read-only object listing ONLY on this app's bucket (not write/delete, not other buckets!)
bucket_viewer = gcp.storage.BucketIAMMember(
    "app-bucket-viewer",
    bucket=bucket.name,
    role="roles/storage.objectViewer",
    member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

bootstrap_image = f"{region}-docker.pkg.dev/{project_id}/demo-apps/demo-api:v1"

service = gcp.cloudrunv2.Service(
    "app-service",
    name=f"demo-api-{stack}",
    location=region,
    ingress="INGRESS_TRAFFIC_ALL",
    deletion_protection=False,
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=app_sa.email,
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
        depends_on=[greeting_version, secret_accessor, bucket_viewer],
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
pulumi.export("service_account", app_sa.email)
pulumi.export("bucket_name", bucket.name)
pulumi.export("service_url", service.uri)
