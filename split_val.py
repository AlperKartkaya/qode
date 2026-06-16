import os
import shutil
import random
from pathlib import Path

random.seed(42)

TRAIN_DIR = Path("data/datasets/qode-vehicle-types/train")
VAL_DIR = Path("data/datasets/qode-vehicle-types/val")

if not TRAIN_DIR.exists():
    print("Train dir not found.")
    exit(1)

VAL_RATIO = 0.15

for class_dir in TRAIN_DIR.iterdir():
    if not class_dir.is_dir():
        continue
        
    class_name = class_dir.name
    val_class_dir = VAL_DIR / class_name
    val_class_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all images in train
    images = list(class_dir.glob("*.*"))
    num_val = int(len(images) * VAL_RATIO)
    
    # Select random images to move to val
    val_images = random.sample(images, num_val)
    
    for img in val_images:
        shutil.move(str(img), str(val_class_dir / img.name))
        
    print(f"[{class_name}] Moved {num_val} images to validation.")
