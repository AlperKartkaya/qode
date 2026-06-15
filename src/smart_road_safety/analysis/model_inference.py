import re
import cv2
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

# Load EasyOCR only when needed to save import time if not used
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            import easyocr
            # Detect GPU availability (CUDA or MPS)
            gpu = torch.cuda.is_available() or torch.backends.mps.is_available()
            # Initialize EasyOCR reader for Turkish and English
            _ocr_engine = easyocr.Reader(['tr', 'en'], gpu=gpu)
            print("Successfully loaded EasyOCR reader.")
        except Exception as e:
            print(f"Warning: Failed to load EasyOCR: {e}. OCR will be mocked.")
            _ocr_engine = None
    return _ocr_engine

# FTR Turkish Plate Pattern
PLATE_PATTERN = re.compile(
    r"^(0[1-9]|[1-7][0-9]|8[01])"
    r"([A-Z]{1}\d{4,5}|[A-Z]{2}\d{3,4}|[A-Z]{3}\d{2,3})$"
)

# Centroid RGB values for competition colors
COMPETITION_COLORS = {
    "beyaz": (240, 240, 240),
    "siyah": (20, 20, 20),
    "gri": (128, 128, 128),
    "kirmizi": (200, 30, 30),
    "mavi": (30, 30, 200),
    "sari": (230, 230, 30),
    "yesil": (30, 180, 30),
    "turuncu": (230, 120, 20),
    "kahverengi": (100, 60, 30)
}

def classify_vehicle_color(crop: np.ndarray) -> str:
    """Classify vehicle color by calculating mean RGB of the center paint area."""
    if crop is None or crop.size == 0:
        return "beyaz"
        
    # Crop the center 50% area to avoid background, tires, or windshield
    h, w, _ = crop.shape
    cy_start, cy_end = int(h * 0.25), int(h * 0.75)
    cx_start, cx_end = int(w * 0.25), int(w * 0.75)
    center_crop = crop[cy_start:cy_end, cx_start:cx_end]
    
    if center_crop.size == 0:
        center_crop = crop
        
    # OpenCV uses BGR, convert mean color to RGB
    mean_bgr = cv2.mean(center_crop)[:3]
    mean_rgb = (mean_bgr[2], mean_bgr[1], mean_bgr[0])
    
    # Find closest centroid
    best_color = "beyaz"
    min_dist = float("inf")
    
    for color_name, centroid in COMPETITION_COLORS.items():
        dist = np.linalg.norm(np.array(mean_rgb) - np.array(centroid))
        if dist < min_dist:
            min_dist = dist
            best_color = color_name
            
    return best_color

def extract_plate_text(crop: np.ndarray) -> str | None:
    """Run OCR on the crop and return a valid Turkish license plate number if found."""
    ocr = get_ocr_engine()
    if ocr is None:
        return None
        
    try:
        # EasyOCR reader.readtext accepts a numpy array or image path
        result = ocr.readtext(crop)
        if not result:
            return None
            
        for bbox, text, confidence in result:
            # Clean plate text (uppercase, alphanumeric, strip spaces)
            cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
            
            # Match regex
            if PLATE_PATTERN.fullmatch(cleaned):
                return cleaned
    except Exception as e:
        print(f"OCR Inference error: {e}")
        
    return None

class SceneAnalysisEngine:
    def __init__(self, yolo_model_name: str = "yolo11x.pt", driver_model_path: str = "data/weights/driver_classifier.pt"):
        # Detect device
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
            
        print(f"Initializing Inference Engine on device: {self.device}")
        
        # Load YOLO Model
        try:
            from ultralytics import YOLO
            self.yolo = YOLO(yolo_model_name)
        except Exception as e:
            print(f"Warning: YOLO load failed: {e}. Bounding boxes will be mocked.")
            self.yolo = None
            
        # Load Driver MobileNetV3 Classifier
        self.driver_classifier = None
        self.driver_classes = []
        
        driver_path = Path(driver_model_path)
        if driver_path.exists():
            try:
                print(f"Loading driver classifier weights from {driver_path}...")
                checkpoint = torch.load(driver_path, map_location=self.device)
                self.driver_classes = checkpoint.get("class_names", ["arkaya_bakma", "etrafa_bakinma", "su_icme", "telefonla_konusma"])
                
                self.driver_classifier = models.mobilenet_v3_small()
                num_features = self.driver_classifier.classifier[3].in_features
                self.driver_classifier.classifier[3] = nn.Linear(num_features, len(self.driver_classes))
                self.driver_classifier.load_state_dict(checkpoint["model_state_dict"])
                self.driver_classifier = self.driver_classifier.to(self.device)
                self.driver_classifier.eval()
            except Exception as e:
                print(f"Warning: Failed to load driver classifier: {e}")
        else:
            print(f"Warning: Driver weights not found at {driver_path}. Driver classifier will be bypassed.")
            
        # Transform for driver crop
        self.driver_transforms = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def analyze_frame(self, frame: np.ndarray, timestamp_seconds: float) -> dict:
        """Run YOLO, OCR, and Driver Classifier on a single frame."""
        h, w, _ = frame.shape
        result = {
            "vehicle_detected": False,
            "vehicle_type": "sedan",
            "vehicle_color": "beyaz",
            "vehicle_confidence": 0.0,
            "plate_text": None,
            "driver_events": []
        }
        
        if self.yolo is None:
            return result
            
        # Run YOLO inference
        yolo_results = self.yolo(frame, verbose=False)[0]
        boxes = yolo_results.boxes
        
        best_vehicle_box = None
        best_vehicle_conf = 0.0
        best_vehicle_cls = None
        
        person_boxes = []
        phone_boxes = []
        laptop_boxes = []
        
        # Class mappings for COCO dataset
        # 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck, 67: cell phone, 63: laptop
        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            
            # Find vehicles
            if cls_id in (2, 3, 5, 7):
                if conf > best_vehicle_conf:
                    best_vehicle_conf = conf
                    best_vehicle_box = box.xyxy[0].cpu().numpy().astype(int)
                    best_vehicle_cls = cls_id
            elif cls_id == 0:  # Person
                person_boxes.append(box.xyxy[0].cpu().numpy().astype(int))
            elif cls_id == 67:  # Cell phone
                phone_boxes.append((box.xyxy[0].cpu().numpy().astype(int), conf))
            elif cls_id == 63:  # Laptop
                laptop_boxes.append((box.xyxy[0].cpu().numpy().astype(int), conf))
                
        # If vehicle is detected
        if best_vehicle_box is not None:
            result["vehicle_detected"] = True
            result["vehicle_confidence"] = best_vehicle_conf
            
            # Map vehicle type
            if best_vehicle_cls == 7:
                result["vehicle_type"] = "kamyon"
            elif best_vehicle_cls == 5:
                result["vehicle_type"] = "minibus"
            else:
                result["vehicle_type"] = "sedan" # Default
                
            # Crop vehicle to extract color and license plate
            x1, y1, x2, y2 = best_vehicle_box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            vehicle_crop = frame[y1:y2, x1:x2]
            
            # Classify vehicle color
            result["vehicle_color"] = classify_vehicle_color(vehicle_crop)
            
            # Run plate OCR on the lower half of the vehicle crop
            vh, vw, _ = vehicle_crop.shape
            lower_half = vehicle_crop[int(vh*0.4):vh, :]
            plate_val = extract_plate_text(lower_half)
            if plate_val:
                result["plate_text"] = plate_val
                
            # Try to locate the driver crop
            driver_crop = None
            
            # Check if any person is inside/intersecting the vehicle box
            driver_box = None
            for pbox in person_boxes:
                px1, py1, px2, py2 = pbox
                # Intersection check
                ix1 = max(x1, px1)
                iy1 = max(y1, py1)
                ix2 = min(x2, px2)
                iy2 = min(y2, py2)
                
                if ix2 > ix1 and iy2 > iy1:
                    driver_box = pbox
                    break
                    
            if driver_box is not None:
                d_x1, d_y1, d_x2, d_y2 = driver_box
                d_x1, d_y1 = max(0, d_x1), max(0, d_y1)
                d_x2, d_y2 = min(w, d_x2), min(h, d_y2)
                driver_crop = frame[d_y1:d_y2, d_x1:d_x2]
            else:
                # Fallback: crop upper windshield area (upper 45% of the vehicle)
                wy1 = y1
                wy2 = min(y2, int(y1 + vh * 0.45))
                wx1 = int(x1 + vw * 0.15)
                wx2 = int(x1 + vw * 0.85)
                wx1, wy1 = max(0, wx1), max(0, wy1)
                wx2, wy2 = min(w, wx2), min(h, wy2)
                if wx2 > wx1 and wy2 > wy1:
                    driver_crop = frame[wy1:wy2, wx1:wx2]
                    
            # Run driver classification
            if driver_crop is not None and driver_crop.size > 0 and self.driver_classifier is not None:
                try:
                    # Convert to PIL Image
                    driver_img = Image.fromarray(cv2.cvtColor(driver_crop, cv2.COLOR_BGR2RGB))
                    input_tensor = self.driver_transforms(driver_img).unsqueeze(0).to(self.device)
                    
                    with torch.no_grad():
                        outputs = self.driver_classifier(input_tensor)
                        probs = torch.softmax(outputs, dim=1)[0]
                        conf, class_idx = torch.max(probs, 0)
                        
                        conf_val = conf.item()
                        predicted_label = self.driver_classes[class_idx.item()]
                        
                        # Only report risk behavior if confidence is solid and it's not a dummy safe state
                        # Custom State Farm label mapping:
                        # safe_driving is mapped out
                        if predicted_label != "safe_driving" and conf_val > 0.65:
                            # Map class name to category and FTR tag
                            # All mapped to "sofor_eylemi" category
                            result["driver_events"].append({
                                "zaman_saniye": timestamp_seconds,
                                "kategori": "sofor_eylemi",
                                "etiket": predicted_label,
                                "confidence_score": conf_val
                            })
                except Exception as e:
                    print(f"Driver classification inference error: {e}")
                    
        # Check for cell phone / laptop detections anywhere as extra cabin objects
        for pbox, pconf in phone_boxes:
            result["driver_events"].append({
                "zaman_saniye": timestamp_seconds,
                "kategori": "nesneler",
                "etiket": "teknocan",
                "confidence_score": pconf
            })
            
        for lbox, lconf in laptop_boxes:
            result["driver_events"].append({
                "zaman_saniye": timestamp_seconds,
                "kategori": "nesneler",
                "etiket": "bilgisayar",
                "confidence_score": lconf
            })
            
        return result
