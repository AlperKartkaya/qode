from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..policy import QodPolicy, load_default_qod_policy
from ..qod import QodDecision

SUPPORTED_QUALITY_PROFILES = {"standard", "boosted"}


def _require_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def _require_profile(value: str) -> str:
    profile = _require_text(value, "profile")
    if profile not in SUPPORTED_QUALITY_PROFILES:
        raise ValueError(f"Unsupported quality profile: {profile}")
    return profile


@dataclass(frozen=True)
class MobileSessionBootstrapRequest:
    phone_number: str
    device_session_id: str
    requested_profile: str = "standard"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "phone_number", _require_text(self.phone_number, "phone_number")
        )
        object.__setattr__(
            self,
            "device_session_id",
            _require_text(self.device_session_id, "device_session_id"),
        )
        object.__setattr__(
            self, "requested_profile", _require_profile(self.requested_profile)
        )


@dataclass(frozen=True)
class MobileSessionBootstrapResult:
    session_id: str
    verified: bool
    active_profile: str
    verification_reference: str
    message: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", _require_text(self.session_id, "session_id")
        )
        object.__setattr__(
            self, "active_profile", _require_profile(self.active_profile)
        )
        object.__setattr__(
            self,
            "verification_reference",
            _require_text(self.verification_reference, "verification_reference"),
        )


@dataclass(frozen=True)
class NumberVerificationRequest:
    phone_number: str
    device_session_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "phone_number", _require_text(self.phone_number, "phone_number")
        )
        object.__setattr__(
            self,
            "device_session_id",
            _require_text(self.device_session_id, "device_session_id"),
        )


@dataclass(frozen=True)
class NumberVerificationResult:
    verified: bool
    verification_reference: str
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "verification_reference",
            _require_text(self.verification_reference, "verification_reference"),
        )


@dataclass(frozen=True)
class QodActivationRequest:
    session_id: str
    target_profile: str
    reason: str
    duration_seconds: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", _require_text(self.session_id, "session_id")
        )
        object.__setattr__(
            self, "target_profile", _require_profile(self.target_profile)
        )
        object.__setattr__(self, "reason", _require_text(self.reason, "reason"))
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive.")


@dataclass(frozen=True)
class QodActivationResult:
    accepted: bool
    applied_profile: str
    request_reference: str
    expires_in_seconds: int | None = None
    denial_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "applied_profile", _require_profile(self.applied_profile)
        )
        object.__setattr__(
            self,
            "request_reference",
            _require_text(self.request_reference, "request_reference"),
        )
        if self.expires_in_seconds is not None and self.expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be positive when provided.")


class NumberVerificationGateway(ABC):
    @abstractmethod
    def verify_number(
        self, request: NumberVerificationRequest
    ) -> NumberVerificationResult:
        raise NotImplementedError


class QualityOnDemandGateway(ABC):
    @abstractmethod
    def activate_quality(self, request: QodActivationRequest) -> QodActivationResult:
        raise NotImplementedError


def build_qod_activation_request(
    session_id: str,
    decision: QodDecision,
    policy: QodPolicy | None = None,
) -> QodActivationRequest | None:
    if not decision.should_activate:
        return None

    active_policy = policy if policy is not None else load_default_qod_policy()
    reason = (
        "; ".join(decision.reasons) if decision.reasons else decision.expected_benefit
    )

    return QodActivationRequest(
        session_id=session_id,
        target_profile=decision.requested_profile,
        reason=reason,
        duration_seconds=active_policy.boosted_duration_seconds,
    )
