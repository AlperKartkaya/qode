import os
import shutil
import uuid
import yaml
import cv2
import random
from pathlib import Path

from src.smart_road_safety.training.build_datasets import (
    process_vehicle_types,
    augment_minority_classes,
    VEHICLE_OUT
)

YOLO_MAPPING = {
    "Bus.v1i.yolov11": {"bus": "minibus"},
    "MINIBUS.v1-minibus.yolov11": {"MID BUS": "minibus"},
    "Suv.v1i.yolov11": {"1": "suv"},
    "Truck.v2i.yolov11": {"Truckrotation": "kamyon"},
    "Van.v1i.yolov11": {"Van": "panelvan"},
    "hatchback-xuv": {"Hatchback": "hatchback", "XUV": "suv"},
    "pickup.v1i.yolov11": {"pickup": "pickup"},
    "sedan.v1i.yolov11": {"sedan": "sedan"}
}

CAR_TYPES_DIR = Path("data/datasets/car-types")
TARGET_TRAIN = VEHICLE_OUT / "train"
TARGET_VAL = VEHICLE_OUT / "val"

def process_yolo_dataset(dataset_dir: Path, mapping: dict):
    yaml_path = dataset_dir / "data.yaml"
    if not yaml_path.exists():
        print(f"Skipping {dataset_dir}, no data.yaml")
        return
        
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
        
    names = data.get("names", [])
    
    # Check train, valid, test folders
    for split in ["train", "valid", "test", "val"]:
        images_dir = dataset_dir / split / "images"
        labels_dir = dataset_dir / split / "labels"
        
        if not images_dir.exists() or not labels_dir.exists():
            continue
            
        for label_file in labels_dir.glob("*.txt"):
            img_file = images_dir / (label_file.stem + ".jpg")
            if not img_file.exists():
                img_file = images_dir / (label_file.stem + ".png")
                if not img_file.exists():
                    img_file = images_dir / (label_file.stem + ".jpeg")
                    if not img_file.exists():
                        continue
                        
            # Read label
            with open(label_file, 'r') as f:
                lines = f.readlines()
                
            img = cv2.imread(str(img_file))
            if img is None:
                continue
                
            h, w = img.shape[:2]
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5: continue
                
                cls_idx = int(parts[0])
                if cls_idx >= len(names): continue
                
                cls_name = names[cls_idx]
                if cls_name not in mapping: continue
                
                target_class = mapping[cls_name]
                out_dir = TARGET_TRAIN / target_class
                out_dir.mkdir(parents=True, exist_ok=True)
                
                x_c, y_c, bw, bh = map(float, parts[1:5])
                
                x1 = int((x_c - bw/2) * w)
                y1 = int((y_c - bh/2) * h)
                x2 = int((x_c + bw/2) * w)
                y2 = int((y_c + bh/2) * h)
                
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w, x2)
                y2 = min(h, y2)
                
                if x2 - x1 < 10 or y2 - y1 < 10:
                    continue
                    
                crop = img[y1:y2, x1:x2]
                out_path = out_dir / f"{uuid.uuid4().hex}.jpg"
                cv2.imwrite(str(out_path), crop)

def build_full_dataset():
    # 1. Reset everything
    print("[1] Temizleniyor...")
    if VEHICLE_OUT.exists():
        shutil.rmtree(VEHICLE_OUT)
        
    TARGET_TRAIN.mkdir(parents=True, exist_ok=True)
    TARGET_VAL.mkdir(parents=True, exist_ok=True)
    
    # 2. Process OLD datasets
    print("[2] Eski veri setleri isleniyor...")
    process_vehicle_types()
    
    # 3. Process NEW YOLO datasets
    print("[3] Yeni YOLO veri setleri isleniyor ve kesiliyor (Crop)...")
    for ds_name, mapping in YOLO_MAPPING.items():
        ds_dir = CAR_TYPES_DIR / ds_name
        if ds_dir.exists():
            process_yolo_dataset(ds_dir, mapping)
            print(f"  -> {ds_name} eklendi.")
            
    # 4. Augment up to 3000
    print("[4] Sınıflar 3000 adede esitleniyor (Augmentation)...")
    augment_minority_classes(VEHICLE_OUT, target_count=3000)
    
    # 5. Split validation
    print("[5] Validation seti ayriliyor (%15)...")
    random.seed(42)
    VAL_RATIO = 0.15
    for class_dir in TARGET_TRAIN.iterdir():
        if not class_dir.is_dir(): continue
        
        class_name = class_dir.name
        val_class_dir = TARGET_VAL / class_name
        val_class_dir.mkdir(parents=True, exist_ok=True)
        
        images = list(class_dir.glob("*.*"))
        num_val = int(len(images) * VAL_RATIO)
        val_images = random.sample(images, num_val)
        
        for img in val_images:
            shutil.move(str(img), str(val_class_dir / img.name))
            
        print(f"[{class_name}] {num_val} resim validation setine aktarildi.")

if __name__ == "__main__":
    build_full_dataset()
