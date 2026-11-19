"""Step 9: Reusable Golden Path — PlatformService ComponentResource."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pulumi
import pulumi_gcp as gcp


@dataclass
class PlatformServiceArgs:
    """Developer-facing contract for onboarding any web service onto the Golden Path."""

    app_name: str
    env: str
    region: str
    project_id: str
    image: str
    team: str
    cost_center: str
    greeting: str
    enable_storage: bool = True
    min_instances: int = 0
    max_instances: int = 3
    cpu: str = "1"
    memory: str = "512Mi"
    extra_env: dict[str, str] = field(default_factory=dict)
    # Set True only when migrating Step 8's root-level resources into this component
    # with zero downtime and zero replacement!
    migrate_from_root: bool = False


class PlatformService(pulumi.ComponentResource):
    """Golden Path abstraction bundling Cloud Run, least-privilege IAM, Secrets,
    optional GCS storage, FinOps guardrails, and SRE Monitoring alerts.
    """

    service_url: pulumi.Output[str]
    service_account: pulumi.Output[str]
    bucket_name: pulumi.Output[str] | None
    alert_policy_name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: PlatformServiceArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("devfest:platform:PlatformService", name, None, opts)
        self._migrate = args.migrate_from_root

        labels = {
            "env": args.env,
            "team": args.team,
            "cost-center": args.cost_center,
            "managed-by": "golden-path",
        }

        # 1. Dedicated least-privilege Service Account
        app_sa = gcp.serviceaccount.Account(
            f"{name}-sa",
            account_id=f"{args.app_name}-{args.env}-sa",
            display_name=f"Least-privilege runtime SA for {args.app_name} ({args.env})",
            opts=self._child_opts("app-sa"),
        )

        # 2. Secret Manager secret + least-privilege accessor role
        greeting_secret = gcp.secretmanager.Secret(
            f"{name}-greeting-secret",
            secret_id=f"{args.app_name}-greeting-{args.env}",
            labels=labels,
            replication=gcp.secretmanager.SecretReplicationArgs(
                auto=gcp.secretmanager.SecretReplicationAutoArgs(),
            ),
            opts=self._child_opts("app-greeting-secret"),
        )

        greeting_version = gcp.secretmanager.SecretVersion(
            f"{name}-greeting-version",
            secret=greeting_secret.id,
            secret_data=args.greeting,
            opts=self._child_opts("app-greeting-version"),
        )

        secret_accessor = gcp.secretmanager.SecretIamMember(
            f"{name}-secret-accessor",
            secret_id=greeting_secret.id,
            role="roles/secretmanager.secretAccessor",
            member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
            opts=self._child_opts("app-secret-accessor"),
        )

        # 3. Optional private GCS bucket + seed file + read-only IAM
        service_deps: list[pulumi.Resource] = [greeting_version, secret_accessor]
        bucket: gcp.storage.Bucket | None = None
        if args.enable_storage:
            bucket = gcp.storage.Bucket(
                f"{name}-storage",
                name=f"{args.project_id}-{args.app_name}-{args.env}",
                location=args.region.upper(),
                uniform_bucket_level_access=True,
                public_access_prevention="enforced",
                force_destroy=True,
                labels=labels,
                lifecycle_rules=(
                    [
                        gcp.storage.BucketLifecycleRuleArgs(
                            action=gcp.storage.BucketLifecycleRuleActionArgs(type="Delete"),
                            condition=gcp.storage.BucketLifecycleRuleConditionArgs(age=30),
                        )
                    ]
                    if args.env == "dev"
                    else []
                ),
                opts=self._child_opts("app-storage"),
            )

            gcp.storage.BucketObject(
                f"{name}-storage-seed",
                name="welcome.json",
                bucket=bucket.name,
                content_type="application/json",
                content=json.dumps(
                    {
                        "message": f"Hello from {args.app_name} storage managed by Golden Path!",
                        "env": args.env,
                        "event": "DevFest Jaen 2026",
                    },
                    indent=2,
                ),
                opts=self._child_opts("app-storage-seed"),
            )

            bucket_viewer = gcp.storage.BucketIAMMember(
                f"{name}-bucket-viewer",
                bucket=bucket.name,
                role="roles/storage.objectViewer",
                member=app_sa.email.apply(lambda email: f"serviceAccount:{email}"),
                opts=self._child_opts("app-bucket-viewer"),
            )
            service_deps.append(bucket_viewer)

        # 4. Cloud Run v2 Service with FinOps caps & app-specific env vars
        env_vars = [
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name="APP_NAME",
                value=args.app_name,
            ),
            gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                name="APP_ENV",
                value=args.env,
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
        ]
        if bucket is not None:
            env_vars.append(
                gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                    name="GCS_BUCKET_NAME",
                    value=bucket.name,
                )
            )
        for key, value in sorted(args.extra_env.items()):
            env_vars.append(
                gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(name=key, value=value)
            )

        service = gcp.cloudrunv2.Service(
            f"{name}-service",
            name=f"{args.app_name}-{args.env}",
            location=args.region,
            ingress="INGRESS_TRAFFIC_ALL",
            deletion_protection=False,
            labels=labels,
            template=gcp.cloudrunv2.ServiceTemplateArgs(
                service_account=app_sa.email,
                labels=labels,
                scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                    min_instance_count=args.min_instances,
                    max_instance_count=args.max_instances,
                ),
                containers=[
                    gcp.cloudrunv2.ServiceTemplateContainerArgs(
                        image=args.image,
                        resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                            limits={"cpu": args.cpu, "memory": args.memory},
                            cpu_idle=True,
                        ),
                        envs=env_vars,
                    )
                ],
            ),
            opts=self._child_opts(
                "app-service",
                depends_on=service_deps,
                ignore_changes=["template.containers[0].image"],
            ),
        )

        gcp.cloudrunv2.ServiceIamMember(
            f"{name}-service-invoker",
            name=service.name,
            location=args.region,
            role="roles/run.invoker",
            member="allUsers",
            opts=self._child_opts("app-service-invoker"),
        )

        # 5. SRE Observability & FinOps spike alert
        alert_threshold = max(1, args.max_instances - 1)
        instance_alert = gcp.monitoring.AlertPolicy(
            f"{name}-instance-alert",
            display_name=f"[FinOps/SRE] High Cloud Run instances - {args.app_name}-{args.env}",
            combiner="OR",
            conditions=[
                gcp.monitoring.AlertPolicyConditionArgs(
                    display_name=f"{args.app_name}-{args.env} active instances > {alert_threshold}",
                    condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                        filter=(
                            'resource.type = "cloud_run_revision" '
                            f'AND resource.labels.service_name = "{args.app_name}-{args.env}" '
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
            user_labels=labels,
            opts=self._child_opts("app-instance-alert"),
        )

        self.service_url = service.uri
        self.service_account = app_sa.email
        self.bucket_name = bucket.name if bucket is not None else None
        self.alert_policy_name = instance_alert.name

        self.register_outputs(
            {
                "service_url": self.service_url,
                "service_account": self.service_account,
                "bucket_name": self.bucket_name,
                "alert_policy_name": self.alert_policy_name,
            }
        )

    def _child_opts(
        self,
        legacy_root_name: str,
        *,
        depends_on: list[pulumi.Resource] | None = None,
        ignore_changes: list[str] | None = None,
    ) -> pulumi.ResourceOptions:
        """Build child ResourceOptions, attaching zero-downtime migration aliases if needed."""
        aliases = (
            [pulumi.Alias(name=legacy_root_name, parent=pulumi.ROOT_STACK_RESOURCE)]
            if self._migrate
            else None
        )
        return pulumi.ResourceOptions(
            parent=self,
            aliases=aliases,
            depends_on=depends_on,
            ignore_changes=ignore_changes,
        )
