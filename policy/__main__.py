"""Python Policy-as-Code (Pulumi CrossGuard) guardrails for FinOps & Security (Step 8+).

Run against any step with:
    pulumi preview --policy-pack policy
    pulumi up --policy-pack policy
"""

from __future__ import annotations

from pulumi_policy import (
    EnforcementLevel,
    PolicyPack,
    ReportViolation,
    ResourceValidationArgs,
    ResourceValidationPolicy,
)

REQUIRED_FINOPS_LABELS = ("env", "team", "cost-center")
ALLOWED_EU_LOCATIONS = {
    "europe-west4",
    "EUROPE-WEST4",
    "europe-west1",
    "EUROPE-WEST1",
    "europe-southwest1",
    "EUROPE-SOUTHWEST1",
}
LABELLED_RESOURCE_TYPES = {
    "gcp:storage/bucket:Bucket",
    "gcp:cloudrunv2/service:Service",
    "gcp:secretmanager/secret:Secret",
}
MAX_CLOUD_RUN_INSTANCES = 10


def _validate_finops_labels(
    args: ResourceValidationArgs, report_violation: ReportViolation
) -> None:
    if args.resource_type not in LABELLED_RESOURCE_TYPES:
        return

    labels = args.props.get("labels") or {}
    missing = [key for key in REQUIRED_FINOPS_LABELS if not labels.get(key)]
    if missing:
        report_violation(
            f"FinOps violation: resource '{args.name}' is missing required labels: "
            f"{', '.join(missing)}."
        )


def _validate_eu_region(
    args: ResourceValidationArgs, report_violation: ReportViolation
) -> None:
    if args.resource_type not in {
        "gcp:storage/bucket:Bucket",
        "gcp:cloudrunv2/service:Service",
    }:
        return

    location = args.props.get("location")
    if location not in ALLOWED_EU_LOCATIONS:
        report_violation(
            f"Data-residency violation: '{args.name}' uses location '{location}'. "
            f"Allowed EU locations: {sorted(ALLOWED_EU_LOCATIONS)}."
        )


def _validate_cloudrun_cost_ceiling(
    args: ResourceValidationArgs, report_violation: ReportViolation
) -> None:
    if args.resource_type != "gcp:cloudrunv2/service:Service":
        return

    template = args.props.get("template") or {}
    scaling = template.get("scaling") or {}
    max_instances = scaling.get("maxInstanceCount")
    min_instances = scaling.get("minInstanceCount") or 0
    labels = args.props.get("labels") or {}

    if max_instances is None or max_instances > MAX_CLOUD_RUN_INSTANCES:
        report_violation(
            f"FinOps ceiling violation: Cloud Run '{args.name}' must set "
            f"max_instance_count <= {MAX_CLOUD_RUN_INSTANCES} (got {max_instances})."
        )

    if labels.get("env") == "dev" and min_instances > 0:
        report_violation(
            f"FinOps scale-to-zero violation: dev Cloud Run '{args.name}' must keep "
            f"min_instance_count == 0 (got {min_instances})."
        )


def _validate_private_gcs_bucket(
    args: ResourceValidationArgs, report_violation: ReportViolation
) -> None:
    if args.resource_type != "gcp:storage/bucket:Bucket":
        return

    if args.props.get("publicAccessPrevention") != "enforced":
        report_violation(
            f"Security violation: GCS bucket '{args.name}' must enforce "
            "public_access_prevention='enforced'."
        )

    if args.props.get("uniformBucketLevelAccess") is not True:
        report_violation(
            f"Security violation: GCS bucket '{args.name}' must enable "
            "uniform_bucket_level_access=True."
        )


PolicyPack(
    name="devfest-platform-guardrails",
    enforcement_level=EnforcementLevel.MANDATORY,
    policies=[
        ResourceValidationPolicy(
            name="require-finops-labels",
            description="All billable resources must include env, team, and cost-center labels.",
            validate=_validate_finops_labels,
        ),
        ResourceValidationPolicy(
            name="require-eu-region",
            description="Data and compute resources must stay in approved EU regions.",
            validate=_validate_eu_region,
        ),
        ResourceValidationPolicy(
            name="cloudrun-cost-ceiling",
            description="Cloud Run services must cap max instances and scale dev to zero.",
            validate=_validate_cloudrun_cost_ceiling,
        ),
        ResourceValidationPolicy(
            name="private-gcs-bucket",
            description="GCS buckets must block public access and enforce uniform bucket-level access.",
            validate=_validate_private_gcs_bucket,
        ),
    ],
)
