# Scenario Evaluation Report

Report version: `scenario-to-score-v1`

## Overall Summary

| Metric | Value |
| --- | --- |
| Scenario count | 3 |
| Expectations met | 3 |
| QoD request rate | 0.67 |
| QoD acceptance rate | 0.33 |
| Avg QoD selectivity | 1.00 |
| Avg policy consistency | 1.00 |
| Avg placeholder label agreement | 1.00 |

## Scenario Table

| Scenario | Status | QoD requested | QoD accepted | Active profile | Expectations met |
| --- | --- | --- | --- | --- | --- |
| qod-denied | PARTIAL | yes | no | standard | yes |
| success | SUCCESS | yes | yes | boosted | yes |
| verification-failed | FAILED | no | no | standard | yes |

## Scenario: `qod-denied`

Verification passes but QoD is denied, resulting in a partial outcome.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | PARTIAL | PARTIAL |
| QoD requested | yes | yes |
| QoD accepted | no | no |
| Active profile | standard | standard |
| Driver risk label | placeholder_none | placeholder_none |

Trace phases: BOOTSTRAP_REQUESTED -> NUMBER_VERIFIED -> QOD_EVALUATED -> QOD_DENIED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.SUCCESS`
- `QOD.REQUEST_REQUIRED`
- `QOD.PROFILE_NOT_AVAILABLE`

QoD rationale:

- candidate target vehicle is close enough to justify boosted quality
- plate is visible but not yet clear enough for reliable reading

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00

## Scenario: `success`

Verified phone number and accepted boosted QoD request.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | SUCCESS | SUCCESS |
| QoD requested | yes | yes |
| QoD accepted | yes | yes |
| Active profile | boosted | boosted |
| Driver risk label | placeholder_none | placeholder_none |

Trace phases: BOOTSTRAP_REQUESTED -> NUMBER_VERIFIED -> QOD_EVALUATED -> QOD_ACTIVATED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.SUCCESS`
- `QOD.REQUEST_REQUIRED`
- `QOD.ACTIVATED`

QoD rationale:

- candidate target vehicle is close enough to justify boosted quality
- plate is visible but not yet clear enough for reliable reading

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00

## Scenario: `verification-failed`

Verification failure stops the workflow before QoD.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | FAILED | FAILED |
| QoD requested | no | no |
| QoD accepted | no | no |
| Active profile | standard | standard |
| Driver risk label | placeholder_none | placeholder_none |

Trace phases: BOOTSTRAP_REQUESTED -> VERIFICATION_FAILED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.VERIFICATION_FAILED`

QoD rationale:

- verification failed

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00
