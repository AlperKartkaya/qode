import json
import time

import pytest

from jobs import JobCapacityError, JobStore


def test_job_store_reserves_capacity_and_releases_it_on_failure(tmp_path, monkeypatch):
    store = JobStore(tmp_path, max_disk_bytes=100, ttl_seconds=3600)
    monkeypatch.setattr(store, "_disk_usage", lambda: 0)
    first, _ = store.allocate("flow", "first", required_capacity=60)
    with pytest.raises(JobCapacityError):
        store.allocate("flow", "second", required_capacity=60)

    store.mark_failed(first.job_id, "UPLOAD_REJECTED")
    second, created = store.allocate("flow", "second", required_capacity=60)
    assert created is True
    assert second.status == "UPLOADING"


def test_restart_marks_interrupted_job_failed_without_secrets(tmp_path):
    job_dir = tmp_path / "job-id"
    (job_dir / "input").mkdir(parents=True)
    (job_dir / "output").mkdir()
    (job_dir / "metadata.json").write_text(
        json.dumps(
            {
                "job_id": "job-id",
                "flow_id": "flow-id",
                "status": "PROCESSING",
                "created_at": time.time(),
                "updated_at": time.time(),
                "checksum_sha256": "a" * 64,
                "duration_seconds": 1.0,
                "failure_code": None,
                "idempotency_key": None,
                "trace": [],
            }
        ),
        encoding="utf-8",
    )

    store = JobStore(tmp_path, max_disk_bytes=1000, ttl_seconds=3600)
    payload = store.public_payload("job-id")

    assert payload["status"] == "FAILED"
    assert payload["failureCode"] == "BACKEND_RESTART_INTERRUPTED"
    assert "token" not in repr(payload).lower()
