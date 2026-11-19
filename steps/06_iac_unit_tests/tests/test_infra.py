"""Unit tests for IaC code using pytest + Pulumi in-memory mocks (zero cloud calls!).

Run from repo root:
    .venv/bin/pytest -v steps/06_iac_unit_tests/tests/
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pulumi

# Allow importing `infra.py` directly from steps/06_iac_unit_tests/
STEP_DIR = Path(__file__).resolve().parent.parent
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))


class GcpMocks(pulumi.runtime.Mocks):
    """In-memory mock engine so infrastructure tests run locally in milliseconds."""

    def new_resource(
        self, args: pulumi.runtime.MockResourceArgs
    ) -> tuple[str | None, dict[str, Any]]:
        outputs = dict(args.inputs)
        if args.typ == "gcp:cloudrunv2/service:Service":
            outputs.setdefault("uri", f"https://{args.name}-mock.a.run.app")
        return f"{args.name}_id", outputs

    def call(self, args: pulumi.runtime.MockCallArgs) -> dict[str, Any]:
        if args.token == "gcp:compute/getDefaultServiceAccount:getDefaultServiceAccount":
            return {"email": "123456789-compute@developer.gserviceaccount.com"}
        return {}


pulumi.runtime.set_mocks(GcpMocks(), preview=False)

from infra import create_app_infrastructure  # noqa: E402

# Instantiate the `prod` infrastructure graph purely in memory (no GCP credentials needed).
prod_infra = create_app_infrastructure(
    stack="prod",
    project_id="mock-devfest-project",
    region="europe-west4",
    manage_registry=True,
    min_instances=0,
    max_instances=5,
)


@pulumi.runtime.test
def test_bucket_enforces_private_access() -> pulumi.Output[None]:
    """BUG 1 check: GCS bucket must block public access and use uniform bucket-level access."""

    def check(args: list[Any]) -> None:
        public_access_prevention, uniform_access = args
        assert public_access_prevention == "enforced", (
            f"Expected public_access_prevention='enforced', got {public_access_prevention!r}"
        )
        assert uniform_access is True, (
            f"Expected uniform_bucket_level_access=True, got {uniform_access!r}"
        )

    return pulumi.Output.all(
        prod_infra.bucket.public_access_prevention,
        prod_infra.bucket.uniform_bucket_level_access,
    ).apply(check)


@pulumi.runtime.test
def test_prod_cloud_run_scaling_avoids_bottleneck() -> pulumi.Output[None]:
    """BUG 2 check: prod must allow at least 2 instances (and stay <= 10 for FinOps)."""

    def check(template: Any) -> None:
        max_instances = template.scaling.max_instance_count
        assert max_instances is not None and 2 <= max_instances <= 10, (
            f"Prod Cloud Run max_instance_count should be between 2 and 10, got {max_instances!r}"
        )

    return prod_infra.service.template.apply(check)


@pulumi.runtime.test
def test_cloud_run_wires_storage_and_secret() -> pulumi.Output[None]:
    """Sanity check: Cloud Run container receives both GCS_BUCKET_NAME and APP_GREETING."""

    def check(template: Any) -> None:
        env_names = {env.name for env in template.containers[0].envs}
        assert "GCS_BUCKET_NAME" in env_names
        assert "APP_GREETING" in env_names

    return prod_infra.service.template.apply(check)
