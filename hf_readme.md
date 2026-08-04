---
license: mit
tags: [qode, smart-road-safety, yolov11, efficientnet]
---

# QoDe-5G runtime models

The authoritative inventory is `config/runtime_assets.json` in the application
repository. It pins repository revision, filename, SHA256, license, expected
class mapping, and model version. `download_weights.sh`, Docker validation and
the upload helper all consume that inventory instead of maintaining separate
lists.

Published at revision `9974f608552ad7bf88a7c7e5a8da56cc767a78f4`:

| File | Role | SHA256 |
|---|---|---|
| `driver_classifier.pt` | Driver actions | `4d83e4d7594c62dafe659c601dfae6cb3cf9c3c58d808ba0b4af9f91a7807f08` |
| `vehicle_type_classifier.pt` | Vehicle type | `56d9b714c5d7d532bd673a021066121ed8cd1ba09637bb9ff12d4e45bb548ff0` |
| `license_plate_detector.pt` | Plate detection | `4c872fd9cfe9268958c382ca8884a2e68c2170d407f4ad2accb261d13014dfa7` |
| `teknocan_detector.pt` | Teknocan detection | `58a786fff875144ff67e6ad83bafe7dfb3687ed69dc1a6b8d32899f765aa1175` |

The YOLO detector checkpoints retain the embedded Ultralytics AGPL-3.0 license;
the repository-level MIT declaration does not replace that upstream obligation.

This repository is **not yet a complete final bundle**. Main-detector and OCR
artifacts still need frozen checksums, and calibrated vehicle-color plus cabin
(seatbelt/computer/passenger-seat) heads must be trained and published. The
final image intentionally refuses to build or start until those blockers are
resolved. No accuracy claim should be inferred from artifact presence alone;
metrics live in the application evidence bundle.
