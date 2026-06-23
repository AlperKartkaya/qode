---
license: mit
tags:
- qode
- smart-road-safety
- yolov11
- efficientnet
- object-detection
- image-classification
---

# QoDe-5G Smart Road Safety Models

This repository contains the fine-tuned computer vision models used in the **QoDe-5G** project for the Smart Road Safety competition.

## Models Included

1. **`license_plate_detector.pt`**
   - **Architecture:** YOLOv11 Nano
   - **Purpose:** Detects license plates on vehicles.
   - **Training Data:** `tr-licence-plates` dataset (~2,000 images).
   - **Performance:** 98.5% mAP on validation set.

2. **`driver_classifier.pt`**
   - **Architecture:** EfficientNet-B2
   - **Purpose:** Classifies driver behavior inside the cabin (e.g., smoking, yawning, seatbelt usage).
   - **Training Data:** State Farm Distracted Driver Detection + custom smoking dataset (~10,000 images).
   - **Performance:** 85.05% validation accuracy (86.82% Macro F1-Score).

3. **`vehicle_type_classifier.pt`**
   - **Architecture:** EfficientNet-B0
   - **Purpose:** Fine-grained vehicle classification (Sedan, SUV, Hatchback, etc.).
   - **Training Data:** Marquis Vehicle Classification + custom vehicle images (~5,000 images).
   - **Performance:** 92.0% validation accuracy (92.0% Macro F1-Score).


4. **`teknocan_detector.pt`**
   - **Architecture:** YOLOv11 Nano
   - **Purpose:** Detects the custom Teknocan object.
   - **Training Data:** Augmented Teknocan dataset.
   - **Performance:** 99.5% mAP50 on validation set.

## Usage

These weights are meant to be used with the `model_inference.py` engine inside the main QoDe repository.
They are automatically downloaded during the Docker build process:

```python
from huggingface_hub import hf_hub_download

# Example download
path = hf_hub_download(
    repo_id="QoDe-5G/qode-models",
    filename="driver_classifier.pt",
    local_dir="./weights"
)
```

## Limitations (Domain Gap)
The driver classifier was trained on dashboard-mounted cameras (State Farm). It may struggle to classify small objects like cell phones when inference is performed from distant, overhead bridge cameras with windshield reflections. In the QoDe system architecture, YOLO bounding box intersections are used as a fallback mechanism to combat this domain gap.
