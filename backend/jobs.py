from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


JOB_STATUSES = {"UPLOADING", "QUEUED", "PROCESSING", "DONE", "FAILED"}


class JobCapacityError(RuntimeError):
    pass


@dataclass
class JobRecord:
    job_id: str
    flow_id: str
    status: str
    created_at: float
    updated_at: float
    checksum_sha256: str | None = None
    duration_seconds: float | None = None
    failure_code: str | None = None
    idempotency_key: str | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)


class JobStore:
    def __init__(self, root: Path, *, max_disk_bytes: int, ttl_seconds: int) -> None:
        if max_disk_bytes <= 0 or ttl_seconds <= 0:
            raise ValueError("job quota and TTL must be positive")
        self.root = Path(root)
        self.max_disk_bytes = max_disk_bytes
        self.ttl_seconds = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, JobRecord] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self._reserved_bytes: dict[str, int] = {}
        self._lock = threading.RLock()
        self._load_existing()

    def allocate(
        self,
        flow_id: str,
        idempotency_key: str | None,
        *,
        required_capacity: int,
    ) -> tuple[JobRecord, bool]:
        with self._lock:
            self._cleanup_expired()
            if idempotency_key:
                existing_id = self._idempotency.get((flow_id, idempotency_key))
                if existing_id:
                    return self._jobs[existing_id], False
            if (
                self._disk_usage()
                + sum(self._reserved_bytes.values())
                + required_capacity
                > self.max_disk_bytes
            ):
                raise JobCapacityError("job disk quota would be exceeded")
            now = time.time()
            record = JobRecord(
                job_id=str(uuid.uuid4()),
                flow_id=flow_id,
                status="UPLOADING",
                created_at=now,
                updated_at=now,
                idempotency_key=idempotency_key,
            )
            record.trace.append(self._event("UPLOAD_ALLOCATED"))
            self._jobs[record.job_id] = record
            self._reserved_bytes[record.job_id] = required_capacity
            if idempotency_key:
                self._idempotency[(flow_id, idempotency_key)] = record.job_id
            self.input_dir(record.job_id).mkdir(parents=True, exist_ok=False)
            self.output_dir(record.job_id).mkdir(parents=True, exist_ok=False)
            self._persist(record)
            return record, True

    def mark_uploaded(self, job_id: str, checksum: str, duration: float) -> JobRecord:
        with self._lock:
            record = self.get(job_id)
            record.checksum_sha256 = checksum
            record.duration_seconds = duration
            self._reserved_bytes.pop(job_id, None)
            self._transition(record, "QUEUED", "UPLOAD_VALIDATED")
            return record

    def mark_processing(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self.get(job_id)
            self._transition(record, "PROCESSING", "INFERENCE_STARTED")
            return record

    def mark_done(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self.get(job_id)
            self._transition(record, "DONE", "RESULT_VALIDATED")
            return record

    def mark_failed(self, job_id: str, code: str) -> JobRecord:
        with self._lock:
            record = self.get(job_id)
            record.failure_code = code
            self._reserved_bytes.pop(job_id, None)
            self._transition(record, "FAILED", code)
            return record

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise KeyError(job_id)
            return record

    def public_payload(self, job_id: str) -> dict[str, Any]:
        record = self.get(job_id)
        return {
            "jobId": record.job_id,
            "flowId": record.flow_id,
            "status": record.status,
            "checksumSha256": record.checksum_sha256,
            "durationSeconds": record.duration_seconds,
            "failureCode": record.failure_code,
        }

    def input_dir(self, job_id: str) -> Path:
        return self.root / job_id / "input"

    def output_dir(self, job_id: str) -> Path:
        return self.root / job_id / "output"

    def metadata_path(self, job_id: str) -> Path:
        return self.root / job_id / "metadata.json"

    def _transition(self, record: JobRecord, status: str, event: str) -> None:
        if status not in JOB_STATUSES:
            raise ValueError(f"Unsupported job status: {status}")
        record.status = status
        record.updated_at = time.time()
        record.trace.append(self._event(event))
        self._persist(record)

    @staticmethod
    def _event(code: str) -> dict[str, Any]:
        return {"code": code, "timestamp": time.time()}

    def _persist(self, record: JobRecord) -> None:
        target = self.metadata_path(record.job_id)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        os.replace(temporary, target)

    def _load_existing(self) -> None:
        for path in self.root.glob("*/metadata.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                record = JobRecord(**payload)
            except (OSError, ValueError, TypeError):
                continue
            if record.status in {"UPLOADING", "QUEUED", "PROCESSING"}:
                record.status = "FAILED"
                record.failure_code = "BACKEND_RESTART_INTERRUPTED"
                record.updated_at = time.time()
                record.trace.append(self._event("BACKEND_RESTART_INTERRUPTED"))
            self._jobs[record.job_id] = record
            if record.idempotency_key:
                self._idempotency[(record.flow_id, record.idempotency_key)] = record.job_id
            self._persist(record)
        self._cleanup_expired()

    def _cleanup_expired(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for job_id, record in tuple(self._jobs.items()):
            if record.updated_at >= cutoff or record.status == "PROCESSING":
                continue
            self._jobs.pop(job_id, None)
            if record.idempotency_key:
                self._idempotency.pop((record.flow_id, record.idempotency_key), None)
            shutil.rmtree(self.root / job_id, ignore_errors=True)

    def _disk_usage(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total
