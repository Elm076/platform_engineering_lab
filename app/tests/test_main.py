"""Unit tests for the FastAPI JSON demo application (Step 4: App CI/CD)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_json(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "demo-api")
    monkeypatch.setenv("APP_ENV", "test")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "demo-api",
        "env": "test",
    }


def test_root_returns_greeting_and_custom_config(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "catalog-api")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("APP_GREETING", "Welcome from Secret Manager!")
    monkeypatch.setenv("CUSTOM_MODE", "catalog-v2")
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "catalog-api",
        "env": "dev",
        "greeting": "Welcome from Secret Manager!",
        "storage_configured": False,
        "custom": {"mode": "catalog-v2"},
    }


def test_storage_disabled_when_bucket_unset(monkeypatch) -> None:
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)

    response = client.get("/storage")

    assert response.status_code == 200
    assert response.json() == {
        "storage": "disabled",
        "bucket": None,
        "count": 0,
        "files": [],
    }


def test_storage_lists_bucket_objects_as_json(monkeypatch) -> None:
    monkeypatch.setenv("GCS_BUCKET_NAME", "my-project-demo-api-prod")
    fake_files = [
        {
            "name": "welcome.json",
            "size_bytes": 84,
            "content_type": "application/json",
        }
    ]

    with patch("app.main._list_bucket_files", return_value=fake_files) as mock_list:
        response = client.get("/storage")

    mock_list.assert_called_once_with("my-project-demo-api-prod")
    assert response.status_code == 200
    assert response.json() == {
        "storage": "enabled",
        "bucket": "my-project-demo-api-prod",
        "count": 1,
        "files": fake_files,
    }
