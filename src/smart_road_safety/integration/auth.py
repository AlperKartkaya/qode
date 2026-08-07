from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable

from .opengateway import AccessToken, NumberVerificationOutcome, QodSessionOutcome


class AuthStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingAuthorization:
    flow_id: str
    state: str
    expires_at: float


@dataclass
class AuthFlow:
    flow_id: str
    status: str
    session_expires_at: float
    token: AccessToken | None = None
    token_expires_at: float | None = None
    masked_phone_number: str | None = None
    verification_correlator: str | None = None
    qod_session_id: str | None = None
    qod_status: str | None = None
    qod_correlator: str | None = None
    return_uri: str | None = None


class AuthSessionStore:
    def __init__(
        self,
        *,
        state_ttl_seconds: int,
        session_ttl_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if state_ttl_seconds <= 0 or session_ttl_seconds <= 0:
            raise ValueError("auth TTL values must be positive")
        self._state_ttl = state_ttl_seconds
        self._session_ttl = session_ttl_seconds
        self._clock = clock
        self._pending_by_state: dict[str, PendingAuthorization] = {}
        self._flows: dict[str, AuthFlow] = {}
        self._lock = threading.RLock()

    def create_pending(self, *, return_uri: str | None = None) -> PendingAuthorization:
        with self._lock:
            self._purge_expired()
            now = self._clock()
            pending = PendingAuthorization(
                flow_id=secrets.token_urlsafe(24),
                state=secrets.token_urlsafe(32),
                expires_at=now + self._state_ttl,
            )
            self._pending_by_state[pending.state] = pending
            self._flows[pending.flow_id] = AuthFlow(
                flow_id=pending.flow_id,
                status="AUTH_PENDING",
                session_expires_at=now + self._session_ttl,
                return_uri=return_uri,
            )
            return pending

    def consume_state(self, state: str) -> str:
        with self._lock:
            pending = self._pending_by_state.pop(state, None)
            if pending is None or pending.expires_at < self._clock():
                raise AuthStateError("OIDC state is invalid, expired, or already used")
            return pending.flow_id

    def authorize(self, flow_id: str, token: AccessToken) -> AuthFlow:
        with self._lock:
            flow = self._require_flow(flow_id)
            now = self._clock()
            flow.token = token
            flow.token_expires_at = now + token.expires_in
            flow.session_expires_at = min(flow.session_expires_at, now + self._session_ttl)
            flow.status = "AUTHORIZED"
            return flow

    def complete_authorization(self, state: str, token: AccessToken) -> AuthFlow:
        return self.authorize(self.consume_state(state), token)

    def require_access_token(self, flow_id: str) -> str:
        with self._lock:
            flow = self._require_flow(flow_id)
            now = self._clock()
            if (
                flow.token is None
                or flow.token_expires_at is None
                or flow.token_expires_at <= now
            ):
                raise AuthStateError("Open Gateway authorization is missing or expired")
            return flow.token.access_token

    def mark_verification(
        self,
        flow_id: str,
        outcome: NumberVerificationOutcome,
        masked_phone_number: str,
    ) -> AuthFlow:
        with self._lock:
            flow = self._require_flow(flow_id)
            flow.masked_phone_number = masked_phone_number
            flow.verification_correlator = outcome.correlator
            flow.status = "VERIFIED" if outcome.verified else "VERIFICATION_FAILED"
            return flow

    def require_verified(self, flow_id: str) -> AuthFlow:
        with self._lock:
            flow = self._require_flow(flow_id)
            if flow.status not in {"VERIFIED", "QOD_AVAILABLE", "QOD_REQUESTED", "QOD_UNAVAILABLE"}:
                raise AuthStateError("Number Verification must succeed before this operation")
            return flow

    def mark_qod(self, flow_id: str, outcome: QodSessionOutcome) -> AuthFlow:
        with self._lock:
            flow = self.require_verified(flow_id)
            flow.qod_session_id = outcome.session_id
            flow.qod_status = outcome.qos_status
            flow.qod_correlator = outcome.correlator
            flow.status = f"QOD_{outcome.qos_status}"
            return flow

    def mark_qod_unavailable(self, flow_id: str, correlator: str) -> AuthFlow:
        with self._lock:
            flow = self.require_verified(flow_id)
            flow.qod_status = "UNAVAILABLE"
            flow.qod_correlator = correlator
            flow.status = "QOD_UNAVAILABLE"
            return flow

    def public_summary(self, flow_id: str) -> dict[str, object]:
        with self._lock:
            flow = self._require_flow(flow_id)
            return {
                "flowId": flow.flow_id,
                "status": flow.status,
                "phoneNumber": flow.masked_phone_number,
                "verificationCorrelator": flow.verification_correlator,
                "qodSessionId": flow.qod_session_id,
                "qosStatus": flow.qod_status,
                "qodCorrelator": flow.qod_correlator,
            }

    def _require_flow(self, flow_id: str) -> AuthFlow:
        self._purge_expired()
        flow = self._flows.get(flow_id)
        if flow is None:
            raise AuthStateError("flow is unknown or expired")
        return flow

    def _purge_expired(self) -> None:
        now = self._clock()
        for state, pending in tuple(self._pending_by_state.items()):
            if pending.expires_at < now:
                self._pending_by_state.pop(state, None)
        for flow_id, flow in tuple(self._flows.items()):
            if flow.session_expires_at < now:
                self._flows.pop(flow_id, None)
