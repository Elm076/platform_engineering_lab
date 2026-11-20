"""Step 8: finOps + SRE observability + Policy-as-Code guardrails."""

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
greeting_value = config.get("greeting") or f"Hola DevFest Jaén 2026 ({stack})!"
min_instances = config.get_int("min_instances") or 0
max_instances = config.get_int("max_instances") or 3
team = config.get("team") or "platform"
cost_center = config.get("cost_center") or "cc-101"

# --- finOps cost-attribution labels enforced by policy/__main__.py ---
finops_labels = {
    "env": stack,
    "team": team,
    "cost-center": cost_center,
    "managed-by": "iac",
}

# --- Storage with finOps labels + 30-day auto-cleanup lifecycle rule in dev ---
bucket = gcp.storage.Bucket(
    "app-storage",
    name=f"{project_id}-demo-api-{stack}",
    location="EUROPE-WEST4",
    uniform_bucket_level_access=True,
    public_access_prevention="enforced",
    force_destroy=True,
    labels=finops_labels,
    lifecycle_rules=(
        [
            gcp.storage.BucketLifecycleRuleArgs(
                action=gcp.storage.BucketLifecycleRuleActionArgs(type="Delete"),
                condition=gcp.storage.BucketLifecycleRuleConditionArgs(age=30),
            )
        ]
        if stack == "dev"
        else []
    ),
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

greeting_secret = gcp.secretmanager.Secret(
    "app-greeting-secret",
    secret_id=f"demo-api-greeting-{stack}",
    labels=finops_labels,
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
        description="Container images for DevFest Jaén 2026 platform demo",
        labels=finops_labels,
    )

# --- DevSecOps least-privilege identity ---
app_sa = gcp.serviceaccount.Account(
    "app-sa",
    account_id=f"demo-api-{stack}-sa",
    display_name=f"Least-privilege runtime SA for demo-api ({stack})",
)

secret_accessor = gcp.secretmanager.SecretIamMember(
    "app-secret-accessor",
    secret_id=greeting_secret.id,
    role="roles/secretmanager.secretAccessor",
    member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

bucket_viewer = gcp.storage.BucketIAMMember(
    "app-bucket-viewer",
    bucket=bucket.name,
    role="roles/storage.objectViewer",
    member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

bootstrap_image = f"{region}-docker.pkg.dev/{project_id}/demo-apps/demo-api:v1"

# --- Cloud Run with finOps labels, CPU/memory ceiling, cpu_idle & scaling cap ---
service = gcp.cloudrunv2.Service(
    "app-service",
    name=f"demo-api-{stack}",
    location=region,
    ingress="INGRESS_TRAFFIC_ALL",
    deletion_protection=False,
    labels=finops_labels,
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=app_sa.email,
        labels=finops_labels,
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=min_instances,
            # Live guardrail demo: temporarily change to 50 and run
            # `pulumi preview --policy-pack policy` to see Policy-as-Code block it!
            max_instance_count=max_instances,
        ),
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=bootstrap_image,
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={"cpu": "1", "memory": "512Mi"},
                    cpu_idle=True,  # finOps: only bill CPU while handling requests
                ),
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

# --- SRE observability + finOps anomaly detection ---
alert_threshold = max(1, max_instances - 1)
instance_alert = gcp.monitoring.AlertPolicy(
    "app-instance-alert",
    display_name=f"[finOps/SRE] High Cloud Run instances - demo-api-{stack}",
    combiner="OR",
    conditions=[
        gcp.monitoring.AlertPolicyConditionArgs(
            display_name=f"demo-api-{stack} active instances > {alert_threshold}",
            condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                filter=(
                    'resource.type = "cloud_run_revision" '
                    f'AND resource.labels.service_name = "demo-api-{stack}" '
                    'AND metric.type = "run.googleapis.com/container/instance_count"'
                ),
                comparison="COMPARISON_GT",
                threshold_value=float(alert_threshold),
                duration="60s",
                aggregations=[
                    gcp.monitoring.AlertPolicyConditionConditionThresholdAggregationArgs(
                        alignment_period="60s",
                        per_series_aligner="ALIGN_MAX",
                    )
                ],
            ),
        )
    ],
    notification_channels=[],
    user_labels=finops_labels,
)

pulumi.export("env", stack)
pulumi.export("service_account", app_sa.email)
pulumi.export("bucket_name", bucket.name)
pulumi.export("seed_file", seed_file.name)
pulumi.export("service_url", service.uri)
pulumi.export("alert_policy_name", instance_alert.name)
