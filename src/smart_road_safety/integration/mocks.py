from __future__ import annotations

from ..policy import load_default_qod_policy
from .contracts import (
    NumberVerificationGateway,
    NumberVerificationRequest,
    NumberVerificationResult,
    QodActivationRequest,
    QodActivationResult,
    QualityOnDemandGateway,
)


class MockNumberVerificationGateway(NumberVerificationGateway):
    def __init__(self, verified_numbers: tuple[str, ...] = ()) -> None:
        self._verified_numbers = set(verified_numbers)
        self.requests: list[NumberVerificationRequest] = []

    def verify_number(
        self, request: NumberVerificationRequest
    ) -> NumberVerificationResult:
        self.requests.append(request)
        normalized_phone = request.phone_number.strip()
        reference = f"mock-nv-{normalized_phone.replace('+', '')}"

        if normalized_phone in self._verified_numbers:
            return NumberVerificationResult(
                verified=True,
                verification_reference=reference,
                reason="VERIFICATION.SUCCESS",
            )

        return NumberVerificationResult(
            verified=False,
            verification_reference=reference,
            reason="NUMBER_VERIFICATION.VERIFICATION_FAILED",
        )


class MockQualityOnDemandGateway(QualityOnDemandGateway):
    def __init__(
        self,
        available_profiles: tuple[str, ...] = ("standard", "boosted"),
        denied_session_ids: tuple[str, ...] = (),
    ) -> None:
        self._available_profiles = set(available_profiles)
        self._denied_session_ids = set(denied_session_ids)
        self.requests: list[QodActivationRequest] = []

    def activate_quality(self, request: QodActivationRequest) -> QodActivationResult:
        self.requests.append(request)
        reference = f"mock-qod-{request.session_id}"
        default_policy = load_default_qod_policy()

        if (
            request.session_id in self._denied_session_ids
            or request.target_profile not in self._available_profiles
        ):
            return QodActivationResult(
                accepted=False,
                applied_profile=default_policy.standard_profile,
                request_reference=reference,
                denial_reason="QOD.PROFILE_NOT_AVAILABLE",
            )

        return QodActivationResult(
            accepted=True,
            applied_profile=request.target_profile,
            request_reference=reference,
            expires_in_seconds=request.duration_seconds,
        )
