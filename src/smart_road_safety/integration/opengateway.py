from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


E164_PATTERN = re.compile(r"^\+[1-9][0-9]{4,14}$")
HASHED_PHONE_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
QOD_STATUSES = {"REQUESTED", "AVAILABLE", "UNAVAILABLE"}


class OpenGatewayError(RuntimeError):
    def __init__(self, status_code: int, code: str, correlator: str) -> None:
        self.status_code = status_code
        self.code = code
        self.correlator = correlator
        super().__init__(f"Open Gateway request failed: status={status_code}, code={code}")


@dataclass(frozen=True)
class AccessToken:
    access_token: str
    token_type: str
    expires_in: int

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("access_token must not be empty")
        if self.token_type.lower() != "bearer":
            raise ValueError("token_type must be Bearer")
        if self.expires_in <= 0:
            raise ValueError("expires_in must be positive")


@dataclass(frozen=True)
class NumberVerificationOutcome:
    verified: bool
    correlator: str


@dataclass(frozen=True)
class QodSessionOutcome:
    session_id: str
    duration: int
    qos_status: str
    correlator: str

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("sessionId must not be empty")
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        if self.qos_status not in QOD_STATUSES:
            raise ValueError(f"Unsupported qosStatus: {self.qos_status}")


class OpenGatewayClient:
    def __init__(
        self,
        *,
        api_root: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        qos_profile: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_root = api_root.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.qos_profile = qos_profile
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def authorization_url(self, state: str, scopes: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "state": state,
                "scope": scopes,
            }
        )
        return f"{self.api_root}/oauth2/authorize?{query}"

    async def exchange_code(self, auth_code: str) -> AccessToken:
        if not auth_code:
            raise ValueError("authorization code must not be empty")
        async with self._client() as client:
            response = await self._send(
                client,
                "POST",
                f"{self.api_root}/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "redirect_uri": self.redirect_uri,
                },
            )
        payload = self._json_object(response)
        try:
            return AccessToken(
                access_token=str(payload["access_token"]),
                token_type=str(payload.get("token_type", "Bearer")),
                expires_in=int(payload["expires_in"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenGatewayError(502, "INVALID_TOKEN_RESPONSE", "token-exchange") from exc

    async def verify_number(
        self,
        access_token: str,
        *,
        phone_number: str | None = None,
        hashed_phone_number: str | None = None,
    ) -> NumberVerificationOutcome:
        if (phone_number is None) == (hashed_phone_number is None):
            raise ValueError("provide exactly one of phone_number or hashed_phone_number")
        if phone_number is not None and E164_PATTERN.fullmatch(phone_number) is None:
            raise ValueError("phone_number must be E.164")
        if (
            hashed_phone_number is not None
            and HASHED_PHONE_PATTERN.fullmatch(hashed_phone_number) is None
        ):
            raise ValueError("hashed_phone_number must be a SHA-256 hexadecimal value")

        correlator = str(uuid.uuid4())
        payload = (
            {"phoneNumber": phone_number}
            if phone_number is not None
            else {"hashedPhoneNumber": hashed_phone_number}
        )
        async with self._client() as client:
            response = await self._send(
                client,
                "POST",
                f"{self.api_root}/number-verification/v1/verify",
                headers=self._bearer_headers(access_token, correlator),
                json=payload,
                correlator=correlator,
            )
        data = self._json_object(response)
        verified = data.get("devicePhoneNumberVerified")
        if not isinstance(verified, bool):
            raise OpenGatewayError(502, "INVALID_NV_RESPONSE", correlator)
        return NumberVerificationOutcome(
            verified=verified,
            correlator=response.headers.get("x-correlator", correlator),
        )

    async def create_qod_session(
        self, access_token: str, duration: int = 60
    ) -> QodSessionOutcome:
        if duration <= 0:
            raise ValueError("duration must be positive")
        correlator = str(uuid.uuid4())
        async with self._client() as client:
            response = await self._send(
                client,
                "POST",
                f"{self.api_root}/quality-on-demand/v1/sessions",
                headers=self._bearer_headers(access_token, correlator),
                json={
                    "duration": duration,
                    "applicationServer": {"ipv4Address": "0.0.0.0/0"},
                    "qosProfile": self.qos_profile,
                },
                correlator=correlator,
            )
        payload = self._json_object(response)
        try:
            return QodSessionOutcome(
                session_id=str(payload["sessionId"]),
                duration=int(payload["duration"]),
                qos_status=str(payload["qosStatus"]),
                correlator=response.headers.get("x-correlator", correlator),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenGatewayError(502, "INVALID_QOD_RESPONSE", correlator) from exc

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
            follow_redirects=False,
        )

    async def _send(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        correlator: str = "token-exchange",
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise OpenGatewayError(504, "UPSTREAM_TIMEOUT", correlator) from exc
        except httpx.HTTPError as exc:
            raise OpenGatewayError(502, "UPSTREAM_TRANSPORT_ERROR", correlator) from exc
        if response.is_success:
            return response
        code = "UPSTREAM_ERROR"
        try:
            error_payload = response.json()
            if isinstance(error_payload, dict) and isinstance(error_payload.get("code"), str):
                code = error_payload["code"]
        except ValueError:
            pass
        raise OpenGatewayError(response.status_code, code, correlator)

    @staticmethod
    def _bearer_headers(access_token: str, correlator: str) -> dict[str, str]:
        if not access_token:
            raise ValueError("access_token must not be empty")
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-correlator": correlator,
        }

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenGatewayError(502, "INVALID_JSON_RESPONSE", "response") from exc
        if not isinstance(payload, dict):
            raise OpenGatewayError(502, "INVALID_JSON_RESPONSE", "response")
        return payload
