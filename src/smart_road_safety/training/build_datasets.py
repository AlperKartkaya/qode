#!/usr/bin/env python3
import os
import shutil
import random
import cv2
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Make sure src is in pythonpath
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from smart_road_safety.training.windshield_simulator import WindshieldSimulator

DRIVER_OUT = Path("data/datasets/qode-driver-behaviors")
VEHICLE_OUT = Path("data/datasets/qode-vehicle-types")

# ── 1. DRIVER BEHAVIORS ───────────────────────────────────────────────────────
def process_driver_behaviors():
    print("--- Sürücü Davranışları Veri Seti Oluşturuluyor ---")
    
    # Kopyalanacak asıl sınıflar (State Farm'dan zaten preprocess edilmişti)
    # Eğer daha önce `data/datasets/processed_state_farm` varsa oradan alalım.
    sf_processed = Path("data/datasets/processed_state_farm")
    if sf_processed.exists():
        print("[Driver] State Farm verileri kopyalanıyor...")
        for split in ["train", "val"]:
            for cls_dir in (sf_processed / split).iterdir():
                if not cls_dir.is_dir(): continue
                out_dir = DRIVER_OUT / split / cls_dir.name
                out_dir.mkdir(parents=True, exist_ok=True)
                for img_path in cls_dir.glob("*.jpg"):
                    if not (out_dir / img_path.name).exists():
                        shutil.copy(img_path, out_dir / img_path.name)
    else:
        print("[Driver] Hata: processed_state_farm bulunamadı. Lütfen önce preprocess_state_farm.py çalıştırın.")

    # Advance Driver Monitoring'den esneme ve sigara ekleme
    adv_root = Path("data/datasets/advance-driver-monitoring-smartcity12")
    if adv_root.exists():
        print("[Driver] Yawn (0) ve Smoking (4) kırpılıyor (Advance Driver Monitoring)...")
        for split in ["Train", "Test"]:
            out_split = "train" if split == "Train" else "val"
            img_dir = adv_root / split / "images"
            lbl_dir = adv_root / split / "labels"
            
            if not img_dir.exists() or not lbl_dir.exists():
                continue
                
            for label_file in lbl_dir.glob("*.txt"):
                with open(label_file, "r") as f:
                    lines = f.readlines()
                
                # Check if it has 0 (yawn) or 4 (smoking)
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) < 5: continue
                    cls_id = int(parts[0])
                    if cls_id == 0:
                        target_cls = "esneme"
                    elif cls_id == 4:
                        target_cls = "sigara_icme"
                    else:
                        continue
                        
                    # Calculate bounding box
                    img_name = label_file.stem + ".jpg" # YOLO labels share name with img
                    img_path = img_dir / img_name
                    if not img_path.exists():
                        continue
                        
                    img = cv2.imread(str(img_path))
                    if img is None: continue
                    h, w = img.shape[:2]
                    
                    cx = float(parts[1]) * w
                    cy = float(parts[2]) * h
                    bw = float(parts[3]) * w
                    bh = float(parts[4]) * h
                    
                    # Expand bbox to capture upper body context (padding factor 3.0)
                    pad_x = bw * 1.5
                    pad_y = bh * 1.5
                    x1 = max(0, int(cx - bw/2 - pad_x))
                    y1 = max(0, int(cy - bh/2 - pad_y))
                    x2 = min(w, int(cx + bw/2 + pad_x))
                    y2 = min(h, int(cy + bh/2 + pad_y))
                    
                    crop = img[y1:y2, x1:x2]
                    if crop.size > 0:
                        out_dir = DRIVER_OUT / out_split / target_cls
                        out_dir.mkdir(parents=True, exist_ok=True)
                        save_path = out_dir / f"adv_{label_file.stem}_{x1}_{y1}.jpg"
                        
                        # Apply windshield simulation (80% chance for domain adaptation)
                        if random.random() < 0.80:
                            # Save temp file, apply sim, load and save
                            cv2.imwrite(str(save_path), crop)
                            WindshieldSimulator.transform_image(str(save_path), str(save_path))
                        else:
                            cv2.imwrite(str(save_path), crop)

def augment_minority_classes(dataset_path: Path, target_count: int = 1500):
    print(f"--- Sınıf Dengeleme Başlıyor ({dataset_path}) ---")
    for split in ["train"]: # Only balance train
        split_dir = dataset_path / split
        if not split_dir.exists(): continue
        
        for cls_dir in split_dir.iterdir():
            if not cls_dir.is_dir(): continue
            imgs = list(cls_dir.glob("*.jpg"))
            count = len(imgs)
            print(f"[{cls_dir.name}] Mevcut Görsel Sayısı: {count}")
            
            if count > 0 and count < target_count:
                needed = target_count - count
                print(f"[{cls_dir.name}] {needed} adet augmentation üretiliyor...")
                
                # Pick random images to augment
                for i in range(needed):
                    src_img = random.choice(imgs)
                    img = cv2.imread(str(src_img))
                    if img is None: continue
                    
                    # Random transformations
                    # Horizontal flip (50% chance)
                    if random.random() > 0.5:
                        img = cv2.flip(img, 1)
                        
                    # Random Brightness/Contrast
                    alpha = random.uniform(0.7, 1.3) # contrast
                    beta = random.uniform(-30, 30)   # brightness
                    img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
                    
                    out_path = cls_dir / f"aug_{i}_{src_img.name}"
                    cv2.imwrite(str(out_path), img)

def process_vehicle_types():
    print("--- Araç Tipleri Veri Seti Oluşturuluyor ---")
    
    # Hedef FTR sınıfları: sedan, suv, hatchback, pickup, minibus, panelvan, kamyon
    class_map = {
        "family sedan": "sedan",
        "taxi": "sedan",
        "sedan": "sedan",
        "hatchback": "hatchback",
        "suv": "suv",
        "jeep": "suv",
        "pickup": "pickup",
        "minibus": "minibus",
        "bus": "minibus",
        "panelvan": "panelvan",
        "van": "panelvan",
        "heavy truck": "kamyon",
        "truck": "kamyon",
        "fire engine": "kamyon",
    }
    
    marquis = Path("data/datasets/vehicle-classification-marquis03")
    vehicle_type = Path("data/datasets/vehicle-type")
    
    for split in ["train", "val"]:
        out_split = split
        if split == "val":
            # Marquis uses test and val, we'll combine them to val
            splits_to_check = ["val", "test"]
        else:
            splits_to_check = ["train"]
            
        for s in splits_to_check:
            # Marquis
            m_dir = marquis / s
            if m_dir.exists():
                for cls_dir in m_dir.iterdir():
                    if not cls_dir.is_dir(): continue
                    mapped = class_map.get(cls_dir.name.lower())
                    if not mapped: continue
                    
                    out_dir = VEHICLE_OUT / out_split / mapped
                    out_dir.mkdir(parents=True, exist_ok=True)
                    for img in cls_dir.glob("*.jpg"):
                        dest = out_dir / f"mq_{img.name}"
                        if not dest.exists(): shutil.copy(img, dest)
            
            # Vehicle Type
            vt_dir = vehicle_type / s
            # the vehicle-type dataset has an extra nested train/ folder
            if (vt_dir / s).exists():
                vt_dir = vt_dir / s
                
            if vt_dir.exists():
                for cls_dir in vt_dir.iterdir():
                    if not cls_dir.is_dir(): continue
                    mapped = class_map.get(cls_dir.name.lower())
                    if not mapped: continue
                    
                    out_dir = VEHICLE_OUT / out_split / mapped
                    out_dir.mkdir(parents=True, exist_ok=True)
                    for img in cls_dir.glob("*.jpg"):
                        dest = out_dir / f"vt_{img.name}"
                        if not dest.exists(): shutil.copy(img, dest)

if __name__ == "__main__":
    process_driver_behaviors()
    augment_minority_classes(DRIVER_OUT, target_count=3000)
    
    process_vehicle_types()
    augment_minority_classes(VEHICLE_OUT, target_count=2000)
    
    print("All dataset pipelines completed successfully!")
