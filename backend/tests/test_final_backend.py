from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app import create_app
from config import Settings
from smart_road_safety.integration.opengateway import (
    AccessToken,
    NumberVerificationOutcome,
    QodSessionOutcome,
    OpenGatewayError,
)


class FakeGateway:
    def __init__(self):
        self.verify_calls = 0
        self.qod_error = None

    def authorization_url(self, state, scopes):
        return "https://gateway.example/oauth2/authorize?" + urlencode(
            {
                "response_type": "code",
                "redirect_uri": "https://backend.example/api/auth/callback",
                "client_id": "client-id",
                "state": state,
                "scope": scopes,
            }
        )

    async def exchange_code(self, code):
        assert code == "authorization-code"
        return AccessToken("backend-only-token", "Bearer", 300)

    async def verify_number(self, access_token, *, phone_number=None, hashed_phone_number=None):
        assert access_token == "backend-only-token"
        self.verify_calls += 1
        return NumberVerificationOutcome(True, "nv-correlator")

    async def create_qod_session(self, access_token, duration):
        assert access_token == "backend-only-token"
        if self.qod_error:
            raise self.qod_error
        return QodSessionOutcome("qod-id", duration, "AVAILABLE", "qod-correlator")


@dataclass(frozen=True)
class FakeRunResult:
    exit_code: int = 0
    message: str = "ok"


class FakeRunner:
    def run(self, input_path: Path, output_dir: Path):
        assert input_path.name == "video.mp4"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "results.json").write_text(
            '{"video_id":"video.mp4","arac_bilgisi":{"tip":"suv","plaka":"34TC8532","renk":"siyah","confidence_score":0.9},"tespitler":[]}',
            encoding="utf-8",
        )
        return FakeRunResult()


class InvalidResultRunner:
    def run(self, input_path: Path, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "results.json").write_text('{"invalid": true}', encoding="utf-8")
        return FakeRunResult()


def build_client(tmp_path, *, gateway=None, runner=None):
    settings = Settings(
        _env_file=None,
        opengw_api_root="https://gateway.example",
        opengw_client_id="client-id",
        opengw_client_secret="client-secret",
        opengw_redirect_uri="https://backend.example/api/auth/callback",
        final_job_root=tmp_path,
        final_ai_image="teknofest-2026/qode-final:test@sha256:" + "a" * 64,
        allowed_origins="http://localhost",
    )
    active_gateway = gateway or FakeGateway()
    app = create_app(settings=settings, gateway=active_gateway, runner=runner or FakeRunner())
    return TestClient(app), active_gateway


def authorize(client):
    start = client.get("/api/auth/start", follow_redirects=False)
    assert start.status_code == 302
    query = parse_qs(urlparse(start.headers["location"]).query)
    assert query["scope"] == [
        "openid dpv:RequestedServiceProvision#quality-on-demand:sessions:create dpv:FraudPreventionAndDetection#number-verification:verify"
    ]
    callback = client.get(
        "/api/auth/callback",
        params={"code": "authorization-code", "state": query["state"][0]},
    )
    assert callback.status_code == 200
    payload = callback.json()
    assert "access_token" not in payload
    return payload["flowId"]


def test_oidc_nv_qod_state_machine_keeps_token_backend_only(tmp_path):
    client, gateway = build_client(tmp_path)
    flow_id = authorize(client)

    before_nv = client.post("/api/qod/sessions", json={"flowId": flow_id, "duration": 60})
    assert before_nv.status_code == 409

    nv = client.post(
        "/api/number-verification/verify",
        json={"flowId": flow_id, "phoneNumber": "+905390000020"},
    )
    assert nv.status_code == 200
    assert nv.json()["devicePhoneNumberVerified"] is True
    assert nv.json()["phoneNumber"] == "+90********20"

    qod = client.post("/api/qod/sessions", json={"flowId": flow_id, "duration": 60})
    assert qod.status_code == 201
    assert qod.json()["streamingAllowed"] is True
    assert qod.json()["qosStatus"] == "AVAILABLE"
    assert "access_token" not in repr(client.get(f"/api/session/{flow_id}").json())
    assert gateway.verify_calls == 1


def test_invalid_and_replayed_oidc_state_fail(tmp_path):
    client, _ = build_client(tmp_path)
    invalid = client.get(
        "/api/auth/callback", params={"code": "authorization-code", "state": "bad"}
    )
    assert invalid.status_code == 400

    start = client.get("/api/auth/start", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    assert client.get(
        "/api/auth/callback", params={"code": "authorization-code", "state": state}
    ).status_code == 200
    replay = client.get(
        "/api/auth/callback", params={"code": "authorization-code", "state": state}
    )
    assert replay.status_code == 400


def test_mobile_auth_returns_to_registered_app_link(tmp_path):
    client, _ = build_client(tmp_path)
    start = client.get("/api/auth/start", params={"mobile": "true"}, follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    callback = client.get(
        "/api/auth/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert callback.status_code == 302
    mobile_uri = urlparse(callback.headers["location"])
    assert f"{mobile_uri.scheme}://{mobile_uri.netloc}{mobile_uri.path}" == "qode://auth/callback"
    flow_id = parse_qs(mobile_uri.query)["flowId"][0]
    assert client.get(f"/api/session/{flow_id}").json()["status"] == "AUTHORIZED"


def test_qod_failure_is_explicit_fail_open(tmp_path):
    gateway = FakeGateway()
    gateway.qod_error = OpenGatewayError(503, "UPSTREAM_UNAVAILABLE", "qod-failed")
    client, _ = build_client(tmp_path, gateway=gateway)
    flow_id = authorize(client)
    client.post(
        "/api/number-verification/verify",
        json={"flowId": flow_id, "phoneNumber": "+905390000020"},
    )

    response = client.post("/api/qod/sessions", json={"flowId": flow_id, "duration": 60})

    assert response.status_code == 200
    assert response.json()["qosStatus"] == "UNAVAILABLE"
    assert response.json()["streamingAllowed"] is True
    assert response.json()["fallbackMaxResolution"] == "240p"


def test_upload_is_job_scoped_idempotent_and_schema_validated(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path)
    flow_id = authorize(client)
    client.post(
        "/api/number-verification/verify",
        json={"flowId": flow_id, "phoneNumber": "+905390000020"},
    )
    monkeypatch.setattr("app.probe_video_duration", lambda path: 113.92)
    video = b"\x00\x00\x00\x18ftypmp42" + b"0" * 64

    first = client.post(
        "/api/videos",
        data={"flow_id": flow_id},
        files={"file": ("../../unsafe.mp4", video, "video/mp4")},
        headers={"Idempotency-Key": "same-upload"},
    )
    assert first.status_code == 202
    second = client.post(
        "/api/videos",
        data={"flow_id": flow_id},
        files={"file": ("other.mp4", video, "video/mp4")},
        headers={"Idempotency-Key": "same-upload"},
    )
    assert second.status_code == 202
    assert second.json()["jobId"] == first.json()["jobId"]

    job_id = first.json()["jobId"]
    status = client.get(f"/api/jobs/{job_id}")
    assert status.json()["status"] == "DONE"
    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    assert result.json()["video_id"] == "video.mp4"
    assert (tmp_path / job_id / "input" / "video.mp4").is_file()
    assert "unsafe" not in str(tmp_path / job_id)


def test_upload_rejects_non_mp4_and_unverified_flow(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path)
    flow_id = authorize(client)
    monkeypatch.setattr("app.probe_video_duration", lambda path: 1.0)

    unverified = client.post(
        "/api/videos",
        data={"flow_id": flow_id},
        files={"file": ("video.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
    )
    assert unverified.status_code == 409

    client.post(
        "/api/number-verification/verify",
        json={"flowId": flow_id, "phoneNumber": "+905390000020"},
    )
    invalid = client.post(
        "/api/videos",
        data={"flow_id": flow_id},
        files={"file": ("video.mp4", b"not-an-mp4", "video/mp4")},
    )
    assert invalid.status_code == 415


def test_container_success_with_invalid_result_marks_job_failed(tmp_path, monkeypatch):
    client, _ = build_client(tmp_path, runner=InvalidResultRunner())
    flow_id = authorize(client)
    client.post(
        "/api/number-verification/verify",
        json={"flowId": flow_id, "phoneNumber": "+905390000020"},
    )
    monkeypatch.setattr("app.probe_video_duration", lambda path: 1.0)
    response = client.post(
        "/api/videos",
        data={"flow_id": flow_id},
        files={"file": ("video.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
    )
    job_id = response.json()["jobId"]
    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "FAILED"
    assert status["failureCode"] == "INVALID_FTR_RESULT"
    assert client.get(f"/api/jobs/{job_id}/result").status_code == 409


def test_legacy_token_and_global_job_endpoints_are_gone(tmp_path):
    client, _ = build_client(tmp_path)
    assert client.post("/auth/token", json={"code": "x"}).status_code == 410
    assert client.post(
        "/nv/verify", json={"access_token": "x", "phone_number": "+905390000020"}
    ).status_code == 410
    assert client.post("/upload", files={"file": ("x.mp4", b"x", "video/mp4")}).status_code == 410
