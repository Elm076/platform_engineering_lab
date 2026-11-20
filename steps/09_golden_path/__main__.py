"""Step 9: Platform engineering payoff — Onboarding 2 different apps via one golden path."""

from __future__ import annotations

import pulumi
import pulumi_gcp as gcp
from platform_service import PlatformService, PlatformServiceArgs

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

if manage_registry:
    gcp.artifactregistry.Repository(
        "app-registry",
        repository_id="demo-apps",
        location=region,
        format="DOCKER",
        description="Container images for DevFest Jaén 2026 platform demo",
        labels={
            "env": stack,
            "team": team,
            "cost-center": cost_center,
            "managed-by": "golden-path",
        },
    )

bootstrap_image = f"{region}-docker.pkg.dev/{project_id}/demo-apps/demo-api:v1"

# App #1: Existing `demo-api` refactored into the golden path with ZERO downtime (via aliases!).
demo_api = PlatformService(
    "demo-api",
    PlatformServiceArgs(
        app_name="demo-api",
        env=stack,
        region=region,
        project_id=project_id,
        image=bootstrap_image,
        team=team,
        cost_center=cost_center,
        greeting=greeting_value,
        enable_storage=True,
        min_instances=min_instances,
        max_instances=max_instances,
        migrate_from_root=True,
    ),
)

# App #2: Brand-new `catalog-api` onboarded in ~10 lines with customized template values!
# Differences from App #1:
#   - Stateless (`enable_storage=False` -> skips GCS bucket, seed file & bucket IAM)
#   - Different team & finOps cost center (`catalog` / `cc-202`)
#   - Higher scaling cap (`max_instances=4`) and custom app-level config (`extra_env`)
# Still inherits least-privilege IAM, Secret Manager, Monitoring alert, and passes Policy-as-Code!
catalog_api = PlatformService(
    "catalog-api",
    PlatformServiceArgs(
        app_name="catalog-api",
        env=stack,
        region=region,
        project_id=project_id,
        image=bootstrap_image,
        team="catalog",
        cost_center="cc-202",
        greeting=f"Welcome to Catalog API ({stack})!",
        enable_storage=False,
        min_instances=0,
        max_instances=4,
        extra_env={
            "CUSTOM_MODE": "catalog-v2",
            "CUSTOM_TIER": "gold",
        },
    ),
)

pulumi.export("env", stack)
pulumi.export("demo_api_url", demo_api.service_url)
pulumi.export("demo_api_seed_file", demo_api.seed_file)
pulumi.export("catalog_api_url", catalog_api.service_url)
