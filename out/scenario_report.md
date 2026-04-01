# Scenario Evaluation Report

Report version: `scenario-to-score-v1`

## Overall Summary

| Metric | Value |
| --- | --- |
| Scenario count | 3 |
| Expectations met | 3 |
| QoD request rate | 1.00 |
| QoD acceptance rate | 1.00 |
| Avg QoD selectivity | 1.00 |
| Avg policy consistency | 1.00 |
| Avg behavior label agreement | 1.00 |

## Scenario Table

| Scenario | Status | QoD requested | QoD accepted | Active profile | Expectations met |
| --- | --- | --- | --- | --- | --- |
| video-1-smoking | SUCCESS | yes | yes | boosted | yes |
| video-2-phone | SUCCESS | yes | yes | boosted | yes |
| video-3-erratic | SUCCESS | yes | yes | boosted | yes |

## Scenario: `video-1-smoking`

Smoking and unsafe scanning are observed while the target vehicle approaches the camera.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | SUCCESS | SUCCESS |
| QoD requested | yes | yes |
| QoD accepted | yes | yes |
| Active profile | boosted | boosted |
| Driver risk label | smoking_and_unsafe_scanning | smoking_and_unsafe_scanning |

Trace phases: BOOTSTRAP_REQUESTED -> NUMBER_VERIFIED -> QOD_EVALUATED -> QOD_ACTIVATED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.SUCCESS`
- `QOD.REQUEST_REQUIRED`
- `QOD.ACTIVATED`

QoD rationale:

- plate is visible but not yet clear enough for reliable reading
- driver risk score suggests a higher-detail inspection window

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00

## Scenario: `video-2-phone`

Phone use is observed while the target vehicle approaches the camera.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | SUCCESS | SUCCESS |
| QoD requested | yes | yes |
| QoD accepted | yes | yes |
| Active profile | boosted | boosted |
| Driver risk label | phone_use_while_driving | phone_use_while_driving |

Trace phases: BOOTSTRAP_REQUESTED -> NUMBER_VERIFIED -> QOD_EVALUATED -> QOD_ACTIVATED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.SUCCESS`
- `QOD.REQUEST_REQUIRED`
- `QOD.ACTIVATED`

QoD rationale:

- plate is visible but not yet clear enough for reliable reading
- driver risk score suggests a higher-detail inspection window

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00

## Scenario: `video-3-erratic`

Erratic, drunk-like driving is observed while the target vehicle approaches the camera.

| Field | Expected | Actual |
| --- | --- | --- |
| Status | SUCCESS | SUCCESS |
| QoD requested | yes | yes |
| QoD accepted | yes | yes |
| Active profile | boosted | boosted |
| Driver risk label | drunk_like_erratic_driving | drunk_like_erratic_driving |

Trace phases: BOOTSTRAP_REQUESTED -> NUMBER_VERIFIED -> QOD_EVALUATED -> QOD_ACTIVATED

Trace context codes:

- `SESSION.BOOTSTRAP_REQUESTED`
- `NUMBER_VERIFICATION.SUCCESS`
- `QOD.REQUEST_REQUIRED`
- `QOD.ACTIVATED`

QoD rationale:

- plate is visible but not yet clear enough for reliable reading
- driver risk score suggests a higher-detail inspection window

Metric snapshot: selectivity=1.00, policy=1.00, labels=1.00
