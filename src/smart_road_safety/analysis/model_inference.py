"""
model_inference.py — QoDe Scene Analysis Engine

Handles all per-frame inference:
  • YOLO11x object/vehicle detection
  • Driver behaviour classification (EfficientNet-B2 or MobileNetV3)
  • Vehicle type classification (EfficientNet-B0 fine-tuned)
  • Passenger zone detection (geometric — arka_koltuk_1/2, on_koltuk)
  • License plate OCR (EasyOCR)
  • Vehicle color classification (K-Means dominant colour)
  • Seatbelt violation detection (heuristic on driver crop)
"""

import re
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from pathlib import Path
from typing import Optional

# ── Lazy-load EasyOCR so startup cost is paid only when first used ────────────

_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            import easyocr
            gpu = torch.cuda.is_available() or torch.backends.mps.is_available()
            _ocr_engine = easyocr.Reader(['tr', 'en'], gpu=gpu)
            print("EasyOCR reader initialised.")
        except Exception as e:
            print(f"Warning: EasyOCR failed to load: {e}. OCR will be skipped.")
            _ocr_engine = None
    return _ocr_engine


# ── Turkish plate regex (FTR spec) ────────────────────────────────────────────

PLATE_PATTERN = re.compile(
    r"^(0[1-9]|[1-7][0-9]|8[01])"
    r"([A-Z]{1}\d{4,5}|[A-Z]{2}\d{3,4}|[A-Z]{3}\d{2,3})$"
)

# ── FTR colour palette (RGB) ──────────────────────────────────────────────────

FTR_COLOURS = {
    "beyaz":      (240, 240, 240),
    "siyah":      (20,  20,  20),
    "gri":        (128, 128, 128),
    "kirmizi":    (200, 30,  30),
    "mavi":       (30,  30,  200),
    "sari":       (230, 230, 30),
    "yesil":      (30,  180, 30),
    "turuncu":    (230, 120, 20),
    "kahverengi": (100, 60,  30),
}

_COLOUR_CENTROIDS = np.array(list(FTR_COLOURS.values()), dtype=np.float32)
_COLOUR_NAMES     = list(FTR_COLOURS.keys())


def classify_vehicle_colour(crop: np.ndarray) -> str:
    """K-Means dominant colour → nearest FTR palette entry."""
    if crop is None or crop.size == 0:
        return "beyaz"

    # Work on centre 60% of crop to avoid background, tyres, glass
    h, w = crop.shape[:2]
    cy0, cy1 = int(h * 0.20), int(h * 0.80)
    cx0, cx1 = int(w * 0.15), int(w * 0.85)
    roi = crop[cy0:cy1, cx0:cx1]
    if roi.size == 0:
        roi = crop

    # Convert BGR → RGB pixel list
    pixels = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float32)

    # K-Means with k=3 to find dominant colours
    k = min(3, len(pixels))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    try:
        _, labels, centres = cv2.kmeans(
            pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )
        # Pick the cluster with most pixels
        counts = np.bincount(labels.flatten())
        dominant_rgb = centres[np.argmax(counts)]
    except Exception:
        dominant_rgb = pixels.mean(axis=0)

    # Nearest neighbour in FTR palette (Euclidean)
    dists = np.linalg.norm(_COLOUR_CENTROIDS - dominant_rgb, axis=1)
    return _COLOUR_NAMES[int(np.argmin(dists))]


def extract_plate_text(crop: np.ndarray) -> Optional[str]:
    """Run EasyOCR on the crop; return a valid Turkish plate string or None."""
    ocr = get_ocr_engine()
    if ocr is None:
        return None
    try:
        results = ocr.readtext(crop)
        for _bbox, text, _conf in results:
            cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
            if PLATE_PATTERN.fullmatch(cleaned):
                return cleaned
    except Exception as e:
        print(f"OCR error: {e}")
    return None


# ── Model loading helpers ─────────────────────────────────────────────────────

def _resolve_weights(local_path: str, docker_path: str) -> Optional[Path]:
    """Return the first existing path among local and Docker candidates."""
    for p in (local_path, docker_path):
        resolved = Path(p)
        if resolved.exists():
            return resolved
    return None


# ── Main scene analysis engine ────────────────────────────────────────────────

class SceneAnalysisEngine:
    """
    Unified inference engine.

    Args:
        yolo_model_name: YOLO model file name (searched in CWD, then /app/weights/).
        driver_model_path: Driver classifier weights (local path).
        vehicle_type_model_path: Vehicle type classifier weights (local path).
    """

    # COCO class IDs we care about
    _VEHICLE_CLS  = {2, 3, 5, 7}        # car, motorcycle, bus, truck
    _PERSON_CLS   = 0
    _PHONE_CLS    = 67
    _LAPTOP_CLS   = 63
    _CIGARETTE_CLS = None                # COCO has no cigarette; handled by driver classifier

    # COCO vehicle → FTR coarse type (refined by vehicle type classifier if available)
    _COCO_TO_FTR_TYPE = {2: "sedan", 3: "sedan", 5: "minibus", 7: "kamyon"}

    def __init__(
        self,
        yolo_model_name: str = "yolo11x.pt",
        driver_model_path: str = "data/weights/driver_classifier.pt",
        vehicle_type_model_path: str = "data/weights/vehicle_type_classifier.pt",
        teknocan_model_path: str = "data/weights/teknocan_detector.pt",
    ):
        # ── Device ───────────────────────────────────────────────────────────
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        print(f"[Engine] Device: {self.device}")

        # ── YOLO ─────────────────────────────────────────────────────────────
        self.yolo = None
        yolo_path = _resolve_weights(yolo_model_name, f"/app/weights/{yolo_model_name}")
        if yolo_path:
            try:
                from ultralytics import YOLO
                self.yolo = YOLO(str(yolo_path))
                print(f"[Engine] YOLO loaded: {yolo_path}")
            except Exception as e:
                print(f"[Engine] YOLO load failed: {e}")
        else:
            print(f"[Engine] YOLO weights not found ({yolo_model_name}). Detection skipped.")

        # ── Teknocan YOLO ─────────────────────────────────────────────────────
        self.teknocan_yolo = None
        tekno_path = _resolve_weights(teknocan_model_path, f"/app/weights/teknocan_detector.pt")
        if tekno_path:
            try:
                from ultralytics import YOLO
                self.teknocan_yolo = YOLO(str(tekno_path))
                print(f"[Engine] Teknocan YOLO loaded: {tekno_path}")
            except Exception as e:
                print(f"[Engine] Teknocan YOLO load failed: {e}")

        # ── Driver behaviour classifier ───────────────────────────────────────
        self.driver_classifier = None
        self.driver_classes: list[str] = []
        self._load_driver_classifier(driver_model_path)

        # ── Vehicle type classifier ───────────────────────────────────────────
        self.vehicle_type_classifier = None
        self.vehicle_type_classes: list[str] = []
        self._load_vehicle_type_classifier(vehicle_type_model_path)

        # ── Image transforms ──────────────────────────────────────────────────
        self._driver_tf = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self._vehicle_tf = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    # ── Loader helpers ────────────────────────────────────────────────────────

    def _load_driver_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/driver_classifier.pt")
        if path is None:
            print(f"[Engine] Driver classifier not found — driver events will be skipped.")
            return
        try:
            ckpt = torch.load(path, map_location=self.device)
            self.driver_classes = ckpt.get(
                "class_names",
                ["arkaya_bakma", "esneme", "etrafa_bakinma", "sigara_icme", "su_icme", "telefonla_konusma"],
            )
            arch = ckpt.get("model_architecture", "mobilenet_v3_small")

            if "efficientnet" in arch:
                # Support EfficientNet-B0 / B2 checkpoints
                model = models.efficientnet_b2(weights=None)
                model.classifier[1] = nn.Linear(
                    model.classifier[1].in_features, len(self.driver_classes)
                )
            else:
                model = models.mobilenet_v3_small(weights=None)
                model.classifier[3] = nn.Linear(
                    model.classifier[3].in_features, len(self.driver_classes)
                )

            model.load_state_dict(ckpt["model_state_dict"])
            model = model.to(self.device).eval()
            self.driver_classifier = model
            print(f"[Engine] Driver classifier loaded ({arch}) — classes: {self.driver_classes}")
        except Exception as e:
            print(f"[Engine] Driver classifier load error: {e}")

    def _load_vehicle_type_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/vehicle_type_classifier.pt")
        if path is None:
            print(f"[Engine] Vehicle type classifier not found — COCO fallback will be used.")
            return
        try:
            ckpt = torch.load(path, map_location=self.device)
            self.vehicle_type_classes = ckpt.get(
                "class_names",
                ["hatchback", "kamyon", "minibus", "panelvan", "pickup", "sedan", "suv"],
            )
            model = models.efficientnet_b0(weights=None)
            model.classifier[1] = nn.Linear(
                model.classifier[1].in_features, len(self.vehicle_type_classes)
            )
            model.load_state_dict(ckpt["model_state_dict"])
            model = model.to(self.device).eval()
            self.vehicle_type_classifier = model
            print(f"[Engine] Vehicle type classifier loaded — classes: {self.vehicle_type_classes}")
        except Exception as e:
            print(f"[Engine] Vehicle type classifier load error: {e}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def _classify_vehicle_type(self, crop: np.ndarray, coco_cls_id: int) -> tuple[str, float]:
        """Return (ftr_type, confidence) for the vehicle crop."""
        if self.vehicle_type_classifier is not None and crop is not None and crop.size > 0:
            try:
                img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                t = self._vehicle_tf(img).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    probs = torch.softmax(self.vehicle_type_classifier(t), dim=1)[0]
                    conf, idx = torch.max(probs, 0)
                return self.vehicle_type_classes[idx.item()], conf.item()
            except Exception as e:
                print(f"Vehicle type classification error: {e}")
        # Fallback: coarse mapping from COCO class
        return self._COCO_TO_FTR_TYPE.get(coco_cls_id, "sedan"), 0.5

    def _classify_driver_action(self, crop: np.ndarray, timestamp: float) -> list[dict]:
        """Run driver classifier on the provided crop. Returns list of detection dicts."""
        if self.driver_classifier is None or crop is None or crop.size == 0:
            return []
        try:
            img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            t = self._driver_tf(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.driver_classifier(t), dim=1)[0]
                conf, idx = torch.max(probs, 0)
            conf_val = conf.item()
            label = self.driver_classes[idx.item()]
            if label != "safe_driving" and conf_val > 0.60:
                return [{
                    "zaman_saniye": timestamp,
                    "kategori": "sofor_eylemi",
                    "etiket": label,
                    "confidence_score": round(conf_val, 4),
                }]
        except Exception as e:
            print(f"Driver classification error: {e}")
        return []

    def _detect_seatbelt_violation(self, driver_crop: np.ndarray, timestamp: float) -> list[dict]:
        """
        Heuristic seatbelt detection on the driver crop.

        Looks for a diagonal high-contrast stripe (the seatbelt strap) running
        from upper-left to lower-right in the upper-body region of the driver crop.
        If no such stripe is found with sufficient confidence we report a violation.

        This is a geometric / signal-processing heuristic — accurate enough as a
        baseline until a dedicated seatbelt model is trained.
        """
        if driver_crop is None or driver_crop.size == 0:
            return []
        try:
            h, w = driver_crop.shape[:2]
            # Focus on the upper 70% torso area
            torso = driver_crop[:int(h * 0.70), :]
            if torso.size == 0:
                return []

            gray = cv2.cvtColor(torso, cv2.COLOR_BGR2GRAY)
            # Canny edge detection
            edges = cv2.Canny(gray, 50, 150)
            # Probabilistic Hough lines for diagonal straps
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, threshold=30,
                minLineLength=int(h * 0.15), maxLineGap=10
            )

            seatbelt_detected = False
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    dx, dy = abs(x2 - x1), abs(y2 - y1)
                    if dx == 0:
                        continue
                    angle = np.degrees(np.arctan2(dy, dx))
                    # A seatbelt strap runs ~25–65 degrees diagonally
                    if 20 < angle < 70 and max(dx, dy) > int(h * 0.12):
                        seatbelt_detected = True
                        break

            if not seatbelt_detected:
                return [{
                    "zaman_saniye": timestamp,
                    "kategori": "sofor_eylemi",
                    "etiket": "emniyet_kemeri_ihlali",
                    "confidence_score": 0.62,
                }]
        except Exception as e:
            print(f"Seatbelt detection error: {e}")
        return []

    def _detect_passengers(
        self,
        person_boxes: list[np.ndarray],
        vehicle_box: np.ndarray,
        timestamp: float,
        frame_w: int,
        is_left_hand_traffic: bool = False,
    ) -> list[dict]:
        """
        Classify persons inside the vehicle bounding box into seat positions.

        Strategy: divide the vehicle box into horizontal thirds (left / middle / right).
        In right-hand traffic (Turkey), the driver sits on the left → persons on the
        right of the driver column are passengers.

        Returns list of detection dicts for yolcular category.
        """
        if not person_boxes:
            return []

        vx1, vy1, vx2, vy2 = vehicle_box
        vw = vx2 - vx1
        vh = vy2 - vy1

        # Vertical midpoint divides front and rear cabin
        front_rear_split = vy1 + int(vh * 0.50)

        # Horizontal thirds: driver | centre | passenger
        h_third = vw / 3
        driver_col_x2   = vx1 + int(h_third)       # left 1/3 = driver (RHT)
        centre_col_x2   = vx1 + int(h_third * 2)   # middle 1/3

        detected_seats: set[str] = set()
        events: list[dict] = []

        for pbox in person_boxes:
            px1, py1, px2, py2 = pbox
            # Compute overlap with vehicle box
            ix1, iy1 = max(vx1, px1), max(vy1, py1)
            ix2, iy2 = min(vx2, px2), min(vy2, py2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue  # No overlap

            # Person centroid
            cx = (px1 + px2) // 2
            cy = (py1 + py2) // 2

            in_front_half = cy < front_rear_split

            if in_front_half:
                if cx > centre_col_x2:
                    seat = "on_koltuk"   # Front-right passenger
                # Front-left is the driver — don't label as passenger
            else:
                # Rear cabin
                if cx < centre_col_x2:
                    seat = "arka_koltuk_1"
                else:
                    seat = "arka_koltuk_2"

            if seat not in detected_seats:
                detected_seats.add(seat)
                events.append({
                    "zaman_saniye": timestamp,
                    "kategori": "yolcular",
                    "etiket": seat,
                    "confidence_score": 0.78,
                })

        return events

    def analyze_frame(self, frame: np.ndarray, timestamp_seconds: float) -> dict:
        """
        Run full inference pipeline on a single BGR frame.

        Returns a dict with:
          vehicle_detected (bool), vehicle_type (str), vehicle_color (str),
          vehicle_confidence (float), plate_text (str|None),
          driver_events (list of FTR detection dicts)
        """
        h, w = frame.shape[:2]
        result: dict = {
            "vehicle_detected": False,
            "vehicle_type": "sedan",
            "vehicle_color": "beyaz",
            "vehicle_confidence": 0.0,
            "plate_text": None,
            "driver_events": [],
        }

        if self.yolo is None:
            return result

        # ── YOLO inference ────────────────────────────────────────────────────
        yolo_out = self.yolo(frame, verbose=False)[0]
        boxes = yolo_out.boxes

        best_vehicle_box: Optional[np.ndarray] = None
        best_vehicle_conf = 0.0
        best_vehicle_cls = 2  # default: car

        person_boxes: list[np.ndarray] = []
        phone_boxes:  list[tuple]      = []
        laptop_boxes: list[tuple]      = []

        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf   = float(box.conf[0].item())
            xyxy   = box.xyxy[0].cpu().numpy().astype(int)

            if cls_id in self._VEHICLE_CLS:
                if conf > best_vehicle_conf:
                    best_vehicle_conf = conf
                    best_vehicle_box  = xyxy
                    best_vehicle_cls  = cls_id
            elif cls_id == self._PERSON_CLS:
                person_boxes.append(xyxy)
            elif cls_id == self._PHONE_CLS:
                phone_boxes.append((xyxy, conf))
            elif cls_id == self._LAPTOP_CLS:
                laptop_boxes.append((xyxy, conf))

        # ── Vehicle-level analysis ────────────────────────────────────────────
        if best_vehicle_box is not None:
            result["vehicle_detected"] = True
            result["vehicle_confidence"] = best_vehicle_conf

            x1, y1, x2, y2 = best_vehicle_box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            vehicle_crop = frame[y1:y2, x1:x2]

            # Vehicle type (fine-grained classifier or COCO fallback)
            vtype, vtype_conf = self._classify_vehicle_type(vehicle_crop, best_vehicle_cls)
            result["vehicle_type"] = vtype

            # Dominant colour via K-Means
            result["vehicle_color"] = classify_vehicle_colour(vehicle_crop)

            # Plate OCR on lower 60% of vehicle crop
            if vehicle_crop.size > 0:
                vh2, vw2 = vehicle_crop.shape[:2]
                lower = vehicle_crop[int(vh2 * 0.40):, :]
                plate = extract_plate_text(lower)
                if plate:
                    result["plate_text"] = plate

            # ── Driver crop ───────────────────────────────────────────────────
            driver_crop = None
            driver_box_used = None

            # Look for a person inside/overlapping the vehicle box
            for pbox in person_boxes:
                px1, py1, px2, py2 = pbox
                ix1 = max(x1, px1); iy1 = max(y1, py1)
                ix2 = min(x2, px2); iy2 = min(y2, py2)
                if ix2 > ix1 and iy2 > iy1:
                    d_x1, d_y1 = max(0, px1), max(0, py1)
                    d_x2, d_y2 = min(w, px2), min(h, py2)
                    driver_crop = frame[d_y1:d_y2, d_x1:d_x2]
                    driver_box_used = pbox
                    break

            if driver_crop is None or driver_crop.size == 0:
                # Fallback: windshield area (upper 45%, inner 70% width)
                vhh, vww = vehicle_crop.shape[:2]
                wy1 = y1
                wy2 = min(y2, int(y1 + vhh * 0.45))
                wx1 = int(x1 + vww * 0.15)
                wx2 = int(x1 + vww * 0.85)
                if wx2 > wx1 and wy2 > wy1:
                    driver_crop = frame[wy1:wy2, wx1:wx2]

            # Driver behaviour classification
            result["driver_events"].extend(
                self._classify_driver_action(driver_crop, timestamp_seconds)
            )

            # Seatbelt violation heuristic (run on driver crop)
            result["driver_events"].extend(
                self._detect_seatbelt_violation(driver_crop, timestamp_seconds)
            )

            # Passenger detection (other persons inside vehicle bbox)
            other_persons = [pb for pb in person_boxes if driver_box_used is None
                             or not np.array_equal(pb, driver_box_used)]
            result["driver_events"].extend(
                self._detect_passengers(
                    other_persons, (x1, y1, x2, y2), timestamp_seconds, w
                )
            )

            # ── Teknocan detection inside vehicle ─────────────────────────────
            if self.teknocan_yolo is not None and vehicle_crop.size > 0:
                try:
                    t_out = self.teknocan_yolo(vehicle_crop, verbose=False)[0]
                    for box in t_out.boxes:
                        t_conf = float(box.conf[0].item())
                        if t_conf > 0.4:  # Threshold to avoid false positives
                            result["driver_events"].append({
                                "zaman_saniye": timestamp_seconds,
                                "kategori": "nesneler",
                                "etiket": "teknocan",
                                "confidence_score": round(t_conf, 4),
                            })
                except Exception as e:
                    print(f"Teknocan detection error: {e}")

        # ── Cabin object detections (anywhere in frame) ───────────────────────
        for _lbox, lconf in laptop_boxes:
            result["driver_events"].append({
                "zaman_saniye": timestamp_seconds,
                "kategori": "nesneler",
                "etiket": "bilgisayar",
                "confidence_score": round(lconf, 4),
            })

        return result
