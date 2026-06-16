import os
import cv2
import uuid
import yaml
import random
from pathlib import Path
import albumentations as A

INPUT_DIR = Path("data/datasets/teknocan")
OUTPUT_DIR = Path("data/datasets/teknocan_augmented")

def read_yolo_label(label_path):
    bboxes = []
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                # YOLO format: class_id x_center y_center width height
                bboxes.append([float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), int(parts[0])])
    return bboxes

def write_yolo_label(label_path, bboxes):
    with open(label_path, 'w') as f:
        for bbox in bboxes:
            f.write(f"{int(bbox[4])} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")

def main():
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
        
    (OUTPUT_DIR / "train" / "images").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "train" / "labels").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "val" / "images").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "val" / "labels").mkdir(parents=True, exist_ok=True)

    # Albumentations pipeline simulating in-car camera conditions
    transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(shift_limit=0.06, scale_limit=0.1, rotate_limit=15, p=0.5),
        A.OneOf([
            A.MotionBlur(blur_limit=(3, 7), p=1.0),
            A.GaussianBlur(blur_limit=(3, 7), p=1.0),
        ], p=0.4),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.3), # Simulate tinted windows
    ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.3))

    images_dir = INPUT_DIR / "images"
    labels_dir = INPUT_DIR / "labels"
    
    if not images_dir.exists() or not labels_dir.exists():
        print("Input images or labels dir not found.")
        return

    all_images = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg")) + list(images_dir.glob("*.png"))
    random.seed(42)
    random.shuffle(all_images)
    
    val_count = int(len(all_images) * 0.15)
    val_images = set(all_images[:val_count])
    
    total_generated = 0
    
    for img_path in all_images:
        label_path = labels_dir / (img_path.stem + ".txt")
        if not label_path.exists():
            continue
            
        bboxes = read_yolo_label(label_path)
        img = cv2.imread(str(img_path))
        if img is None:
            continue
            
        split = "val" if img_path in val_images else "train"
        
        # Save original
        orig_id = uuid.uuid4().hex
        cv2.imwrite(str(OUTPUT_DIR / split / "images" / f"{orig_id}.jpg"), img)
        write_yolo_label(OUTPUT_DIR / split / "labels" / f"{orig_id}.txt", bboxes)
        total_generated += 1
        
        # Generate 5 augmented versions for training only
        if split == "train":
            for _ in range(5):
                try:
                    augmented = transform(image=img, bboxes=bboxes)
                    aug_img = augmented['image']
                    aug_bboxes = augmented['bboxes']
                    
                    if len(aug_bboxes) > 0:
                        aug_id = uuid.uuid4().hex
                        cv2.imwrite(str(OUTPUT_DIR / split / "images" / f"{aug_id}.jpg"), aug_img)
                        write_yolo_label(OUTPUT_DIR / split / "labels" / f"{aug_id}.txt", aug_bboxes)
                        total_generated += 1
                except Exception as e:
                    pass # Ignore augmentation failures (e.g., bounding box out of bounds after crop)

    print(f"Augmentation complete. Generated {total_generated} images.")
    
    yaml_content = {
        'path': str(OUTPUT_DIR.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'names': {0: 'teknocan'}
    }
    
    with open(OUTPUT_DIR / "data.yaml", 'w') as f:
        yaml.dump(yaml_content, f)
    print("Created data.yaml")

if __name__ == "__main__":
    main()
