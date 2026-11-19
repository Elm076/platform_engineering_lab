"""Step 6: Reusable infrastructure builder with 2 intentional bugs for unit testing."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pulumi
import pulumi_gcp as gcp


@dataclass
class AppInfra:
    """Bundle of core resources returned so unit tests can inspect outputs directly."""

    bucket: gcp.storage.Bucket
    seed_file: gcp.storage.BucketObject
    greeting_secret: gcp.secretmanager.Secret
    service: gcp.cloudrunv2.Service


def create_app_infrastructure(
    *,
    stack: str,
    project_id: str,
    region: str = "europe-west4",
    manage_registry: bool = False,
    greeting_value: str | None = None,
    min_instances: int = 0,
    max_instances: int = 5,
) -> AppInfra:
    """Create the application stack (intentionally contains 2 planted bugs for Step 6)."""
    greeting = greeting_value or f"Hola DevFest Jaen 2026 ({stack})!"

    # BUG 1 (Security): Public access prevention disabled and legacy bucket ACLs allowed!
    # Fix live on stage: set uniform_bucket_level_access=True and public_access_prevention="enforced".
    bucket = gcp.storage.Bucket(
        "app-storage",
        name=f"{project_id}-demo-api-{stack}",
        location="EUROPE-WEST4",
        uniform_bucket_level_access=False,
        public_access_prevention="inherited",
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
        secret_data=greeting,
    )

    if manage_registry:
        gcp.artifactregistry.Repository(
            "app-registry",
            repository_id="demo-apps",
            location=region,
            format="DOCKER",
            description="Container images for DevFest Jaen 2026 platform demo",
        )

    default_sa = gcp.compute.get_default_service_account(project=project_id)
    default_sa_secret_access = gcp.secretmanager.SecretIamMember(
        "app-default-sa-secret-access",
        secret_id=greeting_secret.id,
        role="roles/secretmanager.secretAccessor",
        member=f"serviceAccount:{default_sa.email}",
    )

    # BUG 2 (Availability/Logic): Copy-paste error caps prod at a single instance (bottleneck)!
    # Fix live on stage: use `effective_max_instances = max_instances`.
    effective_max_instances = 1 if stack == "prod" else max_instances

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
                max_instance_count=effective_max_instances,
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

    gcp.cloudrunv2.ServiceIamMember(
        "app-service-invoker",
        name=service.name,
        location=region,
        role="roles/run.invoker",
        member="allUsers",
    )

    return AppInfra(
        bucket=bucket,
        seed_file=seed_file,
        greeting_secret=greeting_secret,
        service=service,
    )
