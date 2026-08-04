"""
model_inference.py — QoDe Scene Analysis Engine

Handles all per-frame inference:
  • YOLO11x object/vehicle detection
  • Driver behaviour classification (EfficientNet-B2 or MobileNetV3)
  • Vehicle type classification (EfficientNet-B0 fine-tuned, with TTA & priors)
  • Calibrated cabin detection (passenger seats, seatbelt, computer)
  • License plate OCR (EasyOCR with crop-zoom-enhance preprocessing)
  • License plate detection (YOLO fine-tuned plate detector)
  • Vehicle color classification (K-Means dominant colour)
  • Explicit development-only geometry fallbacks; prohibited in final mode

Enhanced preprocessing pipeline:
  • Driver crop:  windshield ROI → CLAHE → upscale → sharpen
  • Plate crop:   detected region → 4x upscale → grayscale → CLAHE → threshold → deskew
  • Vehicle type:  TTA (flip) + aspect-ratio geometric priors + COCO class anchoring
"""

import re
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from torchvision.transforms import functional as TF
from PIL import Image
from pathlib import Path
from typing import Optional

# ── Lazy-load EasyOCR so startup cost is paid only when first used ────────────

_ocr_engine = None

def get_ocr_engine(strict: bool = False):
    global _ocr_engine
    if _ocr_engine is None:
        try:
            import easyocr
            gpu = torch.cuda.is_available() or torch.backends.mps.is_available()
            _ocr_engine = easyocr.Reader(['tr', 'en'], gpu=gpu)
            print("EasyOCR reader initialised.")
        except Exception as e:
            _ocr_engine = None
            if strict:
                raise RuntimeError(f"EasyOCR failed to load: {e}") from e
            print(f"[Engine] Development OCR unavailable: {e}")
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


# ── OCR character correction for common misreads ─────────────────────────────

# Common OCR character confusions: map from wrong → right
# In Turkish plates: first 2 chars are digits, then letters, then digits
_DIGIT_FIX = {"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "G": "6", "Z": "2", "T": "7"}
_LETTER_FIX = {"0": "O", "1": "I", "5": "S", "8": "B", "6": "G", "2": "Z"}


def _fix_plate_chars(raw: str) -> str:
    """Apply positional character correction to a candidate plate string.

    Turkish plates: DD LLL DDDD (2 digits, 1-3 letters, 2-5 digits).
    First 2 chars must be digits; middle section letters; trailing digits.
    """
    if len(raw) < 5:
        return raw
    # Fix city code (first 2 must be digits)
    fixed = list(raw)
    for i in range(min(2, len(fixed))):
        if fixed[i] in _DIGIT_FIX:
            fixed[i] = _DIGIT_FIX[fixed[i]]
    # Find where letters start (index 2) and where trailing digits begin
    letter_end = 2
    while letter_end < len(fixed) and fixed[letter_end].isalpha():
        letter_end += 1
    # Fix letter section
    for i in range(2, letter_end):
        if fixed[i] in _LETTER_FIX:
            fixed[i] = _LETTER_FIX[fixed[i]]
    # Fix trailing digit section
    for i in range(letter_end, len(fixed)):
        if fixed[i] in _DIGIT_FIX:
            fixed[i] = _DIGIT_FIX[fixed[i]]
    return "".join(fixed)


def _enhance_plate_for_ocr(crop: np.ndarray) -> list[np.ndarray]:
    """Produce multiple enhanced versions of a plate crop for OCR attempts.

    Returns a list of preprocessed images (BGR or grayscale) to try OCR on.
    Pipeline: 4x upscale → CLAHE → adaptive threshold → deskew.
    """
    results: list[np.ndarray] = []
    if crop is None or crop.size == 0:
        return results

    # 1. High-quality 4x upscale
    upscaled = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
    results.append(upscaled)

    # 2. Grayscale + CLAHE (Contrast Limited Adaptive Histogram Equalization)
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    results.append(cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR))

    # 3. Adaptive threshold (binarization for clean OCR)
    binary = cv2.adaptiveThreshold(
        enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )
    results.append(cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR))

    # 4. Otsu threshold variant
    _, otsu = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR))

    # 5. Sharpened version (unsharp mask)
    blurred = cv2.GaussianBlur(upscaled, (0, 0), 3)
    sharpened = cv2.addWeighted(upscaled, 1.5, blurred, -0.5, 0)
    results.append(sharpened)

    # 6. High-contrast grayscale
    high_contrast = cv2.convertScaleAbs(enhanced_gray, alpha=1.8, beta=-50)
    results.append(cv2.cvtColor(high_contrast, cv2.COLOR_GRAY2BGR))

    return results


def _enhance_crop_for_classification(crop: np.ndarray) -> np.ndarray:
    """Enhance a driver/windshield crop for better classification.

    Pipeline: CLAHE contrast enhancement → 2x upscale → unsharp-mask sharpening.
    Designed to cut through windshield tint, reflections, and low resolution.
    """
    if crop is None or crop.size == 0:
        return crop

    # Convert to LAB colour space for CLAHE on luminance only
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # CLAHE on L channel — cuts through glass tint and reflection haze
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)

    enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # 2x upscale with LANCZOS4 (highest quality interpolation)
    h, w = enhanced.shape[:2]
    if h < 200 or w < 200:
        scale = max(2.0, 224 / min(h, w))
        enhanced = cv2.resize(enhanced, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_LANCZOS4)

    # Unsharp mask for sharpening
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.4, blurred, -0.4, 0)

    return sharpened


def preprocess_inference_frame(image: np.ndarray) -> np.ndarray:
    """
    Kapsamlı ön işleme (Denoise -> Anti-Glare -> Sharpening).
    Yapay zekaya gitmeden önce zorlu koşulları temizler.
    """
    if image is None or image.size == 0:
        return image
        
    # Görüntünün ortalama parlaklığını (Luma) ölç
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    mean_brightness = np.mean(v_channel)
    
    processed = image.copy()
    
    # 1. Düşük Işık / Gece Kumlanma Giderici (Bilateral Filter)
    if mean_brightness < 80:
        processed = cv2.bilateralFilter(processed, d=5, sigmaColor=50, sigmaSpace=50)
        
    # 2. Aşırı Parlama (Anti-Glare / Gamma + CLAHE)
    elif mean_brightness > 130:
        gamma = 1.0 - ((mean_brightness - 130) / 255.0) * 0.5
        gamma = max(0.4, gamma)
        
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                          for i in np.arange(0, 256)]).astype("uint8")
        
        gamma_corrected = cv2.LUT(processed, table)
        
        lab = cv2.cvtColor(gamma_corrected, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        
        merged = cv2.merge((cl, a, b))
        processed = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        
    # 3. Hareket Bulanıklığı Giderici (Unsharp Masking)
    # Hafif bir keskinleştirme ile kenarları ve plakaları belirginleştir
    blurred = cv2.GaussianBlur(processed, (0, 0), 2.0)
    final_image = cv2.addWeighted(processed, 1.2, blurred, -0.2, 0)
    
    return final_image


def extract_plate_prediction(crop: np.ndarray, strict: bool = False) -> tuple[Optional[str], float]:
    """Run EasyOCR on multiple enhanced versions of the plate crop.

    Tries original 2x, then 4x LANCZOS4, CLAHE, adaptive threshold, Otsu,
    sharpened, and high-contrast variants. Returns the best valid Turkish plate
    string or None.
    """
    ocr = get_ocr_engine(strict=strict)
    if ocr is None or crop is None or crop.size == 0:
        return None, 0.0

    # Collect all candidate reads across multiple preprocessing variants
    candidates: dict[str, float] = {}  # plate_text → best_confidence

    def _try_ocr(img: np.ndarray) -> None:
        """Run OCR on one image variant and accumulate valid candidates."""
        try:
            results = ocr.readtext(img)
            for _bbox, text, conf in results:
                cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
                # Try raw cleaned text
                if PLATE_PATTERN.fullmatch(cleaned):
                    candidates[cleaned] = max(candidates.get(cleaned, 0.0), conf)
                # Try with character correction
                fixed = _fix_plate_chars(cleaned)
                if fixed != cleaned and PLATE_PATTERN.fullmatch(fixed):
                    candidates[fixed] = max(candidates.get(fixed, 0.0), conf * 0.95)
        except Exception:
            pass

    # Try original with 2x upscale (legacy approach)
    resized_2x = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _try_ocr(resized_2x)

    # Try all enhanced variants
    for enhanced_img in _enhance_plate_for_ocr(crop):
        _try_ocr(enhanced_img)

    # Also try the raw crop
    _try_ocr(crop)

    if candidates:
        # Return the candidate with highest confidence
        best = max(candidates, key=candidates.get)
        return best, float(candidates[best])

    return None, 0.0


def extract_plate_text(crop: np.ndarray, strict: bool = False) -> Optional[str]:
    """Backward-compatible text-only wrapper for support tooling."""
    return extract_plate_prediction(crop, strict=strict)[0]


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
        smoker_model_path: str = "data/weights/smoker_classifier.pt",
        vehicle_type_model_path: str = "data/weights/vehicle_type_classifier.pt",
        vehicle_color_model_path: str = "data/weights/vehicle_color_classifier.pt",
        teknocan_model_path: str = "data/weights/teknocan_detector.pt",
        plate_model_path: str = "data/weights/license_plate_detector.pt",
        cabin_model_path: str = "data/weights/cabin_detector.pt",
        allow_degraded: bool = False,
    ):
        self.allow_degraded = allow_degraded
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
                self._load_failure("Main detector", e)
        else:
            if not self.allow_degraded:
                raise RuntimeError("Main detector weights are required in final mode")
            print(f"[Engine] Main detector unavailable in development mode: {yolo_model_name}")

        # ── Teknocan YOLO ─────────────────────────────────────────────────────
        self.teknocan_yolo = None
        tekno_path = _resolve_weights(teknocan_model_path, f"/app/weights/teknocan_detector.pt")
        if tekno_path:
            try:
                from ultralytics import YOLO
                self.teknocan_yolo = YOLO(str(tekno_path))
                print(f"[Engine] Teknocan YOLO loaded: {tekno_path}")
            except Exception as e:
                self._load_failure("Teknocan detector", e)
        elif not self.allow_degraded:
            raise RuntimeError("Teknocan detector weights are required in final mode")

        self.cabin_yolo = None
        cabin_path = _resolve_weights(cabin_model_path, "/app/weights/cabin_detector.pt")
        if cabin_path:
            try:
                from ultralytics import YOLO
                self.cabin_yolo = YOLO(str(cabin_path))
                print(f"[Engine] Cabin detector loaded: {cabin_path}")
            except Exception as e:
                self._load_failure("Cabin detector", e)
        elif not self.allow_degraded:
            raise RuntimeError("Cabin detector weights are required in final mode")

        # ── License plate detector (YOLO fine-tuned) ──────────────────────────
        self.plate_detector = None
        plate_det_path = _resolve_weights(
            plate_model_path,
            "/app/weights/license_plate_detector.pt",
        )
        if plate_det_path:
            try:
                from ultralytics import YOLO
                self.plate_detector = YOLO(str(plate_det_path))
                print(f"[Engine] Plate detector loaded: {plate_det_path}")
            except Exception as e:
                self._load_failure("Plate detector", e)
        else:
            if not self.allow_degraded:
                raise RuntimeError("Plate detector weights are required in final mode")
            print("[Engine] Plate detector unavailable; development crop fallback enabled")

        # ── Driver behaviour classifier ───────────────────────────────────────
        self.driver_classifier = None
        self.driver_classes: list[str] = []
        self.smoker_classifier = None

        self._load_driver_classifier(driver_model_path)
        self._load_smoker_classifier(smoker_model_path)

        # ── Vehicle type classifier ───────────────────────────────────────────
        self.vehicle_type_classifier = None
        self.vehicle_type_classes: list[str] = []
        self._load_vehicle_type_classifier(vehicle_type_model_path)

        self.vehicle_color_classifier = None
        self.vehicle_color_classes: list[str] = []
        self._load_vehicle_color_classifier(vehicle_color_model_path)

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

        if self.yolo is None and not self.allow_degraded:
            raise RuntimeError("Main detector weights are required in final mode")
        get_ocr_engine(strict=not self.allow_degraded)

    def _load_failure(self, component: str, error: Exception) -> None:
        if not self.allow_degraded:
            raise RuntimeError(f"{component} failed to load: {error}") from error
        print(f"[Engine] Development fallback: {component} failed to load: {error}")

    # ── Loader helpers ────────────────────────────────────────────────────────

    def _load_driver_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/driver_classifier.pt")
        if path is None:
            if not self.allow_degraded:
                raise RuntimeError("Driver classifier weights are required in final mode")
            print("[Engine] Driver classifier unavailable in development mode")
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
            self._load_failure("Driver classifier", e)

    def _load_smoker_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/smoker_classifier.pt")
        if not path:
            print("[Engine] No smoker classifier found; smoking detection will be disabled or fallback.")
            return
        try:
            model = torch.jit.load(path, map_location=self.device)
            self.smoker_classifier = model
            self.smoker_classifier.eval()
            print(f"[Engine] Smoker classifier loaded from {path}")
        except Exception as e:
            if not self.allow_degraded:
                raise RuntimeError(f"Failed to load smoker classifier: {e}") from e
            print(f"[Engine] Development degraded (smoker): {e}")

    def _load_vehicle_type_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/vehicle_type_classifier.pt")
        if path is None:
            if not self.allow_degraded:
                raise RuntimeError("Vehicle type classifier weights are required in final mode")
            print("[Engine] Vehicle classifier unavailable; development COCO fallback enabled")
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
            self._load_failure("Vehicle type classifier", e)

    def _load_vehicle_color_classifier(self, local_path: str) -> None:
        path = _resolve_weights(local_path, "/app/weights/vehicle_color_classifier.pt")
        if path is None:
            if not self.allow_degraded:
                raise RuntimeError("Vehicle color classifier weights are required in final mode")
            print("[Engine] Vehicle color classifier unavailable; development palette fallback enabled")
            return
        try:
            ckpt = torch.load(path, map_location=self.device)
            self.vehicle_color_classes = ckpt["class_names"]
            model = models.efficientnet_b0(weights=None)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(self.vehicle_color_classes))
            model.load_state_dict(ckpt["model_state_dict"])
            self.vehicle_color_classifier = model.to(self.device).eval()
        except Exception as e:
            self._load_failure("Vehicle color classifier", e)

    # ── Inference ─────────────────────────────────────────────────────────────

    def _classify_vehicle_type(self, crop: np.ndarray, coco_cls_id: int) -> tuple[str, float]:
        """Return (ftr_type, confidence) for the vehicle crop.

        Uses Test-Time Augmentation (TTA) with horizontal flip, aspect-ratio
        geometric priors, and COCO class anchoring for front/rear view robustness.
        """
        if self.vehicle_type_classifier is not None and crop is not None and crop.size > 0:
            try:
                img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

                # ── TTA: original + horizontal flip, average probabilities ────
                t_orig = self._vehicle_tf(img).unsqueeze(0).to(self.device)
                t_flip = self._vehicle_tf(TF.hflip(img)).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    p_orig = torch.softmax(self.vehicle_type_classifier(t_orig), dim=1)[0]
                    p_flip = torch.softmax(self.vehicle_type_classifier(t_flip), dim=1)[0]
                    probs = (p_orig + p_flip) / 2.0

                # ── Aspect-ratio geometric prior ─────────────────────────────
                h_crop, w_crop = crop.shape[:2]
                aspect = w_crop / max(h_crop, 1)

                # Front/rear views (aspect > 1.2) make hatchback vs sedan ambiguous;
                # apply geometric corrections:
                if aspect > 1.2 and self.vehicle_type_classes:
                    # Height heuristic: hatchbacks are shorter than sedans from front
                    # For very wide aspect ratios, reduce confidence for ambiguous types
                    idx_map = {name: i for i, name in enumerate(self.vehicle_type_classes)}

                    # COCO class anchoring: if YOLO says truck/bus, strongly bias
                    if coco_cls_id == 7 and "kamyon" in idx_map:  # truck
                        probs[idx_map["kamyon"]] += 0.3
                    elif coco_cls_id == 5 and "minibus" in idx_map:  # bus
                        probs[idx_map["minibus"]] += 0.3
                    elif coco_cls_id in (2, 3):  # car / motorcycle
                        # Penalise panelvan (commonly confused from front)
                        if "panelvan" in idx_map:
                            probs[idx_map["panelvan"]] *= 0.5
                        # From front view, short cars → hatchback; tall → SUV
                        if aspect > 1.6:  # Very wide → likely sedan or hatchback
                            if "kamyon" in idx_map:
                                probs[idx_map["kamyon"]] *= 0.3
                            if "minibus" in idx_map:
                                probs[idx_map["minibus"]] *= 0.3

                    # Re-normalise probabilities
                    probs = probs / probs.sum()

                conf, idx = torch.max(probs, 0)
                predicted = self.vehicle_type_classes[idx.item()]
                conf_val = conf.item()

                # Low-confidence fallback: if less than 0.35, use COCO mapping
                if conf_val < 0.35 and self.allow_degraded:
                    fallback = self._COCO_TO_FTR_TYPE.get(coco_cls_id, "sedan")
                    return fallback, conf_val

                return predicted, conf_val

            except Exception as e:
                if not self.allow_degraded:
                    raise RuntimeError(f"Vehicle classification failed: {e}") from e
                print(f"[Engine] Development vehicle classification fallback: {e}")
        # Fallback: coarse mapping from COCO class
        if not self.allow_degraded:
            raise RuntimeError("Vehicle classifier produced no valid final prediction")
        return self._COCO_TO_FTR_TYPE.get(coco_cls_id, "sedan"), 0.5

    def _extract_face_crop(self, driver_crop: np.ndarray) -> np.ndarray:
        """Extracts the face from the driver crop using Haar Cascade or a geometric fallback."""
        if driver_crop is None or driver_crop.size == 0:
            return driver_crop
            
        h, w = driver_crop.shape[:2]
        gray = cv2.cvtColor(driver_crop, cv2.COLOR_BGR2GRAY)
        
        # Load OpenCV's built-in Haar Cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        
        if len(faces) > 0:
            # Get the largest face
            faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
            x, y, fw, fh = faces[0]
            
            # Expand the crop slightly to include mouth and chin (for smoking/yawning)
            margin_x = int(fw * 0.2)
            margin_y = int(fh * 0.3)
            fx1 = max(0, x - margin_x)
            fy1 = max(0, y - margin_y)
            fx2 = min(w, x + fw + margin_x)
            fy2 = min(h, y + fh + int(margin_y * 1.5)) # More margin at the bottom for mouth/cigarette
            
            return driver_crop[fy1:fy2, fx1:fx2]
            
        # Fallback: top 35% of the driver crop
        return driver_crop[0:int(h * 0.35), :]

    def _classify_smoker(self, face_crop: np.ndarray, timestamp: float) -> list[dict]:
        """Run dedicated smoker classifier on the face crop."""
        if self.smoker_classifier is None or face_crop is None or face_crop.size == 0:
            return []
        try:
            img = Image.fromarray(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB))
            t = self._driver_tf(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.smoker_classifier(t), dim=1)[0]
                conf, idx = torch.max(probs, 0)
            conf_val = conf.item()
            
            # Assuming smoker_classifier outputs binary [not_smoking, smoking] or similar
            # For now, we will map idx==1 to sigara_icme if confidence is high
            if idx.item() == 1 and conf_val > 0.60:
                return [{
                    "zaman_saniye": timestamp,
                    "kategori": "sofor_eylemi",
                    "etiket": "sigara_icme",
                    "confidence_score": round(conf_val, 4),
                }]
        except Exception as e:
            print(f"[Engine] Smoker classifier error: {e}")
        return []

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
            if not self.allow_degraded:
                raise RuntimeError(f"Driver classification failed: {e}") from e
            print(f"[Engine] Development driver classifier error: {e}")
        return []

    def _classify_vehicle_color(self, crop: np.ndarray) -> tuple[str, float]:
        if self.vehicle_color_classifier is not None and crop is not None and crop.size > 0:
            try:
                image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                tensor = self._vehicle_tf(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    probabilities = torch.softmax(self.vehicle_color_classifier(tensor), dim=1)[0]
                confidence, index = torch.max(probabilities, 0)
                return self.vehicle_color_classes[index.item()], float(confidence.item())
            except Exception as e:
                if not self.allow_degraded:
                    raise RuntimeError(f"Vehicle color classification failed: {e}") from e
        if not self.allow_degraded:
            raise RuntimeError("Vehicle color classifier produced no valid final prediction")
        return classify_vehicle_colour(crop), 0.5

    def _detect_cabin_events(self, crop: np.ndarray, timestamp: float) -> list[dict]:
        if self.cabin_yolo is None or crop is None or crop.size == 0:
            if not self.allow_degraded:
                raise RuntimeError("Cabin detector produced no final prediction")
            return []
        events: list[dict] = []
        output = self.cabin_yolo(crop, verbose=False)[0]
        names = output.names
        for box in output.boxes:
            confidence = float(box.conf[0].item())
            label = names[int(box.cls[0].item())]
            if confidence < 0.4:
                continue
            categories = {
                "emniyet_kemeri_ihlali": "sofor_eylemi",
                "bilgisayar": "nesneler",
                "arka_koltuk_1": "yolcular",
                "arka_koltuk_2": "yolcular",
                "on_koltuk": "yolcular",
            }
            if label not in categories:
                raise RuntimeError(f"Unmapped cabin detector class: {label}")
            category = categories[label]
            events.append({
                "zaman_saniye": timestamp,
                "kategori": category,
                "etiket": label,
                "confidence_score": round(confidence, 4),
            })
        return events

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
        rear_seat_counter = 1

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

            # Calculate relative area to infer depth (rear seat passengers appear smaller)
            person_area = (px2 - px1) * (py2 - py1)
            vehicle_area = vw * vh
            is_rear_seat = (person_area / (vehicle_area + 1e-5)) < 0.12

            if not is_rear_seat:
                if cx > centre_col_x2:
                    seat = "on_koltuk"   # Front-right passenger
                else:
                    continue  # Front-left is the driver — don't label as passenger
            else:
                # Rear cabin: dynamically assign arka_koltuk_1, arka_koltuk_2
                # Limit to max 2 rear passengers to comply with FTR schema
                if rear_seat_counter > 2:
                    continue
                seat = f"arka_koltuk_{rear_seat_counter}"
                rear_seat_counter += 1

            if seat.startswith("arka_koltuk") or seat not in detected_seats:
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
        # Comprehensive Preprocessing (Anti-Glare / Denoise / Sharpen)
        frame = preprocess_inference_frame(frame)
        
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
            result["vehicle_box"] = best_vehicle_box.tolist()

            x1, y1, x2, y2 = best_vehicle_box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            vehicle_crop = frame[y1:y2, x1:x2]

            # Vehicle type (fine-grained classifier or COCO fallback)
            vtype, vtype_conf = self._classify_vehicle_type(vehicle_crop, best_vehicle_cls)
            result["vehicle_type"] = vtype

            color, color_confidence = self._classify_vehicle_color(vehicle_crop)
            result["vehicle_color"] = color
            result["vehicle_confidence"] = min(best_vehicle_conf, vtype_conf, color_confidence)

            # Plate OCR
            if vehicle_crop.size > 0:
                plate_img = None
                # Eğer plaka modeli varsa, onu kullanarak plakanın tam yerini bul
                if getattr(self, 'plate_detector', None) is not None:
                    plate_results = self.plate_detector(vehicle_crop, verbose=False)
                    if len(plate_results) > 0 and len(plate_results[0].boxes) > 0:
                        # En yüksek confidence'lı plakayı al
                        boxes = plate_results[0].boxes
                        best_plate = max(boxes, key=lambda x: x.conf[0].item())
                        px1, py1, px2, py2 = map(int, best_plate.xyxy[0].tolist())
                        
                        # Plakayı hafifçe genişlet (margin) harfler kesilmesin
                        margin = 5
                        px1 = max(0, px1 - margin)
                        py1 = max(0, py1 - margin)
                        px2 = min(vehicle_crop.shape[1], px2 + margin)
                        py2 = min(vehicle_crop.shape[0], py2 + margin)
                        
                        plate_img = vehicle_crop[py1:py2, px1:px2]
                
                # Eğer plaka modeli yoksa veya bulamadıysa, eski (ilkel) yönteme dön (Alt %40)
                if (plate_img is None or plate_img.size == 0) and self.allow_degraded:
                    vh2, vw2 = vehicle_crop.shape[:2]
                    plate_img = vehicle_crop[int(vh2 * 0.40):, :]

                plate, plate_confidence = extract_plate_prediction(plate_img, strict=not self.allow_degraded)
                if plate:
                    result["plate_text"] = plate
                    result["vehicle_confidence"] = min(result["vehicle_confidence"], plate_confidence)

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
                # Fallback: windshield area (upper 50%, inner 70% width)
                # This is the typical outer-camera view where the driver is
                # visible through the windshield glass.
                vhh, vww = vehicle_crop.shape[:2]
                wy1 = y1
                wy2 = min(y2, int(y1 + vhh * 0.50))
                wx1 = int(x1 + vww * 0.15)
                wx2 = int(x1 + vww * 0.85)
                if wx2 > wx1 and wy2 > wy1:
                    driver_crop = frame[wy1:wy2, wx1:wx2]

            # ── Enhance driver crop for through-windshield classification ─────
            # Applies CLAHE + upscale + sharpen to cut through glass tint/reflections
            if driver_crop is not None and driver_crop.size > 0:
                driver_crop = _enhance_crop_for_classification(driver_crop)

            # Check for phone usage via YOLO bounding boxes (deterministic override)
            yolo_phone_detected = False
            yolo_phone_confidence = 0.0
            if driver_box_used is not None:
                dx1, dy1, dx2, dy2 = driver_box_used
                for pbox, pconf in phone_boxes:
                    px1, py1, px2, py2 = pbox
                    # Check for intersection between phone and driver person box
                    ix1 = max(dx1, px1); iy1 = max(dy1, py1)
                    ix2 = min(dx2, px2); iy2 = min(dy2, py2)
                    if ix2 > ix1 and iy2 > iy1:
                        yolo_phone_detected = True
                        yolo_phone_confidence = max(yolo_phone_confidence, float(pconf))
                        break

            # Driver behaviour classification (Body)
            action_events = self._classify_driver_action(driver_crop, timestamp_seconds)
            
            # Filter out sigara_icme from old driver model just in case it still predicts it
            action_events = [e for e in action_events if e["etiket"] != "sigara_icme"]
            
            # Smoker classification (Face Crop)
            face_crop = self._extract_face_crop(driver_crop)
            smoker_events = self._classify_smoker(face_crop, timestamp_seconds)
            action_events.extend(smoker_events)
            
            # Eğer YOLO elinde telefon gördüyse, görüntü sınıflandırıcısının yanılması (esneme/sigara) engellenir.
            if yolo_phone_detected:
                action_events = [e for e in action_events if e["etiket"] not in ["telefonla_konusma", "esneme", "sigara_icme", "su_icme", "safe_driving"]]
                action_events.append({
                    "zaman_saniye": timestamp_seconds,
                    "kategori": "sofor_eylemi",
                    "etiket": "telefonla_konusma",
                    "confidence_score": round(yolo_phone_confidence, 4)
                })

            result["driver_events"].extend(action_events)

            if self.allow_degraded:
                result["driver_events"].extend(self._detect_seatbelt_violation(driver_crop, timestamp_seconds))
                other_persons = [pb for pb in person_boxes if driver_box_used is None
                                 or not np.array_equal(pb, driver_box_used)]
                result["driver_events"].extend(
                    self._detect_passengers(other_persons, (x1, y1, x2, y2), timestamp_seconds, w)
                )
            else:
                result["driver_events"].extend(self._detect_cabin_events(vehicle_crop, timestamp_seconds))

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
                    if not self.allow_degraded:
                        raise RuntimeError(f"Teknocan detection failed: {e}") from e
                    print(f"[Engine] Development Teknocan detection error: {e}")

        # ── Cabin object detections (anywhere in frame) ───────────────────────
        for _lbox, lconf in laptop_boxes:
            result["driver_events"].append({
                "zaman_saniye": timestamp_seconds,
                "kategori": "nesneler",
                "etiket": "bilgisayar",
                "confidence_score": round(lconf, 4),
            })

        return result
