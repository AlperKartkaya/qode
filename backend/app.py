from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from smart_road_safety.competition.ftr import read_ftr_result
from smart_road_safety.integration.auth import AuthSessionStore, AuthStateError
from smart_road_safety.integration.opengateway import OpenGatewayClient, OpenGatewayError

from config import Settings, settings as default_settings
from container_runner import ContainerInferenceRunner
from jobs import JobCapacityError, JobStore


class NumberVerificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    flow_id: str = Field(alias="flowId")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    hashed_phone_number: str | None = Field(default=None, alias="hashedPhoneNumber")


class QodRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    flow_id: str = Field(alias="flowId")
    duration: int = Field(default=60, ge=1)


def mask_phone_number(phone_number: str | None) -> str | None:
    if phone_number is None:
        return None
    if len(phone_number) <= 5:
        return "*" * len(phone_number)
    return phone_number[:3] + "*" * (len(phone_number) - 5) + phone_number[-2:]


def remux_to_mp4(source: Path) -> None:
    """Remux an MPEG-TS file to MP4 in-place using ffmpeg (copy, no re-encode)."""
    tmp_mp4 = source.with_suffix(".remux.mp4")
    process = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(source),
            "-c", "copy",
            "-movflags", "+faststart",
            str(tmp_mp4),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if process.returncode != 0:
        tmp_mp4.unlink(missing_ok=True)
        raise ValueError(f"ffmpeg remux failed: {process.stderr[:300]}")
    os.replace(tmp_mp4, source)


def probe_video_duration(path: Path) -> float:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if process.returncode != 0:
        raise ValueError("uploaded file is not a probeable MP4")
    duration = float(process.stdout.strip())
    if duration <= 0:
        raise ValueError("uploaded video duration must be positive")
    return duration


def append_query_parameter(uri: str, name: str, value: str) -> str:
    parts = urlsplit(uri)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append((name, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class DummyInferenceRunner:
    def run(self, input_path: Path, output_dir: Path) -> Any:
        import subprocess
        import sys
        from container_runner import RunnerResult
        output_dir.mkdir(parents=True, exist_ok=True)
        # Call the dummy_ai.py script
        dummy_script = Path(__file__).parent / "dummy_ai" / "dummy_ai.py"
        try:
            # We copy the logic of dummy_ai.py manually since the script hardcodes /app/data/output
            import json
            import time
            time.sleep(3)
            mock_result = {
                "arac_bilgisi": {"tip": "Sedan (Dummy)", "plaka": "34DUMMY123", "renk": "Beyaz", "confidence_score": 0.98},
                "tespitler": [
                    {"zaman_saniye": 1, "kategori": "Risk", "etiket": "Emniyet Kemeri Yok", "confidence_score": 0.90},
                    {"zaman_saniye": 4, "kategori": "Dikkat", "etiket": "Telefona Bakıyor", "confidence_score": 0.85}
                ]
            }
            result_path = output_dir / "results.json"
            result_path.write_text(json.dumps(mock_result))
            return RunnerResult(0, "COMPLETED")
        except Exception as exc:
            return RunnerResult(1, f"DUMMY_ERROR_{type(exc).__name__.upper()}")

def create_app(
    *,
    settings: Settings = default_settings,
    gateway: Any | None = None,
    runner: Any | None = None,
) -> FastAPI:
    app = FastAPI(title="QoDe Final Backend API", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )
    active_gateway = gateway or OpenGatewayClient(
        api_root=settings.opengw_api_root,
        client_id=settings.opengw_client_id,
        client_secret=settings.opengw_client_secret,
        redirect_uri=settings.opengw_redirect_uri,
        qos_profile=settings.opengw_qos_profile,
        timeout_seconds=settings.opengw_timeout_seconds,
    )
    if settings.final_ai_image.lower() == "dummy":
        active_runner = runner or DummyInferenceRunner()
    else:
        active_runner = runner or ContainerInferenceRunner(
            image=settings.final_ai_image,
            use_gpu=settings.use_gpu,
            timeout_seconds=settings.container_timeout_seconds,
        )
    auth_store = AuthSessionStore(
        state_ttl_seconds=settings.auth_state_ttl_seconds,
        session_ttl_seconds=settings.session_ttl_seconds,
    )
    jobs = JobStore(
        settings.final_job_root,
        max_disk_bytes=settings.max_job_disk_bytes,
        ttl_seconds=settings.job_ttl_seconds,
    )
    app.state.settings = settings
    app.state.gateway = active_gateway
    app.state.auth_store = auth_store
    app.state.jobs = jobs
    app.state.runner = active_runner

    def auth_error(exc: AuthStateError, status_code: int = 409) -> HTTPException:
        return HTTPException(status_code=status_code, detail={"code": "FLOW_STATE_INVALID", "message": str(exc)})

    def run_job(job_id: str) -> None:
        jobs.mark_processing(job_id)
        input_path = jobs.input_dir(job_id) / "video.mp4"
        output_dir = jobs.output_dir(job_id)
        result = active_runner.run(input_path, output_dir)
        if result.exit_code != 0:
            jobs.mark_failed(job_id, f"{result.message}_CODE_{result.exit_code}")
            return
        
        json_path = output_dir / "results.json"
        try:
            read_ftr_result(json_path)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            error_details = type(exc).__name__
            if isinstance(exc, ValueError):
                error_details = str(exc).replace(" ", "_")[:50]
            jobs.mark_failed(job_id, f"INVALID_JSON_{error_details}")
            return
        jobs.mark_done(job_id)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "gatewayConfigured": all(
                [settings.opengw_client_id, settings.opengw_client_secret, settings.opengw_redirect_uri]
            ),
            "jobRootWritable": os.access(settings.final_job_root, os.W_OK),
        }

    @app.get("/api/auth/start")
    def auth_start(mobile: bool = False) -> RedirectResponse:
        try:
            settings.require_gateway_config()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "GATEWAY_CONFIG_MISSING"}) from exc
        pending = auth_store.create_pending(
            return_uri=settings.mobile_auth_return_uri if mobile else None
        )
        return RedirectResponse(
            active_gateway.authorization_url(pending.state, settings.opengw_scopes),
            status_code=302,
        )

    @app.get("/api/auth/callback")
    async def auth_callback(code: str, state: str) -> Response:
        try:
            flow_id = auth_store.consume_state(state)
        except AuthStateError as exc:
            raise auth_error(exc, 400) from exc
        try:
            token = await active_gateway.exchange_code(code)
        except OpenGatewayError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": exc.code, "correlator": exc.correlator},
            ) from exc
        flow = auth_store.authorize(flow_id, token)
        if flow.return_uri:
            return RedirectResponse(
                append_query_parameter(flow.return_uri, "flowId", flow_id),
                status_code=302,
            )
        return JSONResponse(auth_store.public_summary(flow_id))

    @app.get("/api/session/{flow_id}")
    def session_summary(flow_id: str) -> dict[str, object]:
        try:
            return auth_store.public_summary(flow_id)
        except AuthStateError as exc:
            raise auth_error(exc, 404) from exc

    @app.post("/api/number-verification/verify")
    async def verify_number(request: NumberVerificationRequest) -> dict[str, Any]:
        try:
            access_token = auth_store.require_access_token(request.flow_id)
            outcome = await active_gateway.verify_number(
                access_token,
                phone_number=request.phone_number,
                hashed_phone_number=request.hashed_phone_number,
            )
        except AuthStateError as exc:
            raise auth_error(exc, 401) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_PHONE_IDENTIFIER"}) from exc
        except OpenGatewayError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "correlator": exc.correlator},
            ) from exc
        masked = mask_phone_number(request.phone_number)
        auth_store.mark_verification(request.flow_id, outcome, masked or "sha256:masked")
        return {
            "flowId": request.flow_id,
            "devicePhoneNumberVerified": outcome.verified,
            "phoneNumber": masked,
            "correlator": outcome.correlator,
        }

    @app.post("/api/qod/sessions")
    async def create_qod_session(request: QodRequest) -> Response:
        try:
            auth_store.require_verified(request.flow_id)
            access_token = auth_store.require_access_token(request.flow_id)
        except AuthStateError as exc:
            raise auth_error(exc) from exc
        try:
            outcome = await active_gateway.create_qod_session(access_token, request.duration)
        except OpenGatewayError as exc:
            auth_store.mark_qod_unavailable(request.flow_id, exc.correlator)
            return JSONResponse(
                status_code=200,
                content={
                    "flowId": request.flow_id,
                    "qosStatus": "UNAVAILABLE",
                    "streamingAllowed": True,
                    "fallbackMaxResolution": "240p",
                    "reasonCode": exc.code,
                    "correlator": exc.correlator,
                },
            )
        auth_store.mark_qod(request.flow_id, outcome)
        return JSONResponse(
            status_code=201,
            content={
                "flowId": request.flow_id,
                "sessionId": outcome.session_id,
                "duration": outcome.duration,
                "qosStatus": outcome.qos_status,
                "streamingAllowed": True,
                "correlator": outcome.correlator,
            },
        )

    @app.delete("/api/qod/sessions/{session_id}", status_code=204)
    def delete_qod_session(session_id: str) -> None:
        """Mock deleting a QoD session early."""
        return None

    @app.post("/api/videos", status_code=202)
    async def upload_video(
        background_tasks: BackgroundTasks,
        flow_id: str = Form(...),
        file: UploadFile = File(...),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        try:
            auth_store.require_verified(flow_id)
        except AuthStateError as exc:
            raise auth_error(exc) from exc
        # Removed content_type check completely to avoid 415 errors. Magic byte check (ftyp) will validate it instead.
        try:
            record, created = jobs.allocate(
                flow_id,
                idempotency_key,
                required_capacity=settings.max_upload_bytes,
            )
        except JobCapacityError as exc:
            raise HTTPException(status_code=507, detail={"code": "JOB_DISK_QUOTA"}) from exc
        if not created:
            return jobs.public_payload(record.job_id)

        temporary = jobs.input_dir(record.job_id) / ".video.mp4.upload"
        target = jobs.input_dir(record.job_id) / "video.mp4"
        digest = hashlib.sha256()
        total = 0
        header = b""
        try:
            with temporary.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.max_upload_bytes:
                        raise HTTPException(status_code=413, detail={"code": "UPLOAD_TOO_LARGE"})
                    if len(header) < 32:
                        header += chunk[: 32 - len(header)]
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            is_mp4 = len(header) >= 12 and header[4:8] == b"ftyp"
            is_mpegts = len(header) >= 1 and header[0:1] == b"\x47"
            if not (is_mp4 or is_mpegts):
                raise HTTPException(status_code=415, detail={"code": "INVALID_VIDEO_SIGNATURE"})
            os.replace(temporary, target)
            if is_mpegts and not is_mp4:
                remux_to_mp4(target)
            duration = probe_video_duration(target)
        except HTTPException:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            jobs.mark_failed(record.job_id, "UPLOAD_REJECTED")
            raise
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            jobs.mark_failed(record.job_id, "INVALID_VIDEO")
            raise HTTPException(status_code=422, detail={"code": "INVALID_VIDEO"}) from exc

        jobs.mark_uploaded(record.job_id, digest.hexdigest(), duration)
        background_tasks.add_task(run_job, record.job_id)
        return jobs.public_payload(record.job_id)

    @app.get("/api/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        try:
            return jobs.public_payload(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"}) from exc

    @app.get("/api/jobs/{job_id}/result")
    def job_result(job_id: str) -> dict[str, Any]:
        try:
            record = jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"}) from exc
        if record.status != "DONE":
            raise HTTPException(status_code=409, detail={"code": "JOB_NOT_DONE"})
        return read_ftr_result(jobs.output_dir(job_id) / "results.json").to_dict()

    @app.get("/api/jobs/{job_id}/trace")
    def job_trace(job_id: str) -> dict[str, Any]:
        try:
            record = jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"}) from exc
        return {"jobId": job_id, "events": record.trace}

    def legacy_gone() -> None:
        raise HTTPException(status_code=410, detail={"code": "P5_ENDPOINT_REPLACED"})

    app.add_api_route("/auth/token", legacy_gone, methods=["POST"])
    app.add_api_route("/nv/verify", legacy_gone, methods=["POST"])
    app.add_api_route("/qod/session", legacy_gone, methods=["POST"])
    app.add_api_route("/upload", legacy_gone, methods=["POST"])
    app.add_api_route("/ai-run", legacy_gone, methods=["POST"])
    app.add_api_route("/ai-result", legacy_gone, methods=["GET"])
    return app


app = create_app()
