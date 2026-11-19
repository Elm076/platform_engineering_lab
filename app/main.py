"""Minimal JSON FastAPI application for the DevFest Jaen 2026 Platform Engineering demo."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.cloud import storage

app = FastAPI(
    title="DevFest Jaen 2026 Demo API",
    version="1.0.0",
)


def _list_bucket_files(bucket_name: str) -> list[dict[str, Any]]:
    """List objects stored in the given GCS bucket."""
    client = storage.Client()
    return [
        {
            "name": blob.name,
            "size_bytes": blob.size,
            "content_type": blob.content_type,
        }
        for blob in client.list_blobs(bucket_name)
    ]


def _get_custom_config() -> dict[str, str]:
    """Collect optional app-specific settings injected with the CUSTOM_ prefix."""
    prefix = "CUSTOM_"
    return {
        key[len(prefix) :].lower(): value
        for key, value in sorted(os.environ.items())
        if key.startswith(prefix)
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness and readiness check."""
    return {
        "status": "ok",
        "service": os.getenv("APP_NAME", "demo-api"),
        "env": os.getenv("APP_ENV", "clickops"),
    }


@app.get("/")
def root() -> dict[str, Any]:
    """Return service metadata and greeting (wired from Secret Manager in Step 3+)."""
    response: dict[str, Any] = {
        "service": os.getenv("APP_NAME", "demo-api"),
        "env": os.getenv("APP_ENV", "clickops"),
        "greeting": os.getenv(
            "APP_GREETING",
            "Hello DevFest Jaen 2026! (deployed via ClickOps)",
        ),
        "storage_configured": bool(os.getenv("GCS_BUCKET_NAME")),
    }
    custom = _get_custom_config()
    if custom:
        response["custom"] = custom
    return response


@app.get("/storage")
def list_storage() -> JSONResponse:
    """List objects in the configured GCS bucket as JSON."""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        return JSONResponse(
            status_code=200,
            content={
                "storage": "disabled",
                "bucket": None,
                "count": 0,
                "files": [],
            },
        )

    try:
        files = _list_bucket_files(bucket_name)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={
                "storage": "error",
                "bucket": bucket_name,
                "detail": str(exc),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "storage": "enabled",
            "bucket": bucket_name,
            "count": len(files),
            "files": files,
        },
    )
