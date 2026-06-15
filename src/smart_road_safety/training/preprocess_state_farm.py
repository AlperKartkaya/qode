import os
import csv
import random
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .windshield_simulator import WindshieldSimulator

# FTR mapped classes for State Farm c0-c9
STATE_FARM_TO_FTR = {
    "c1": "telefonla_konusma",
    "c2": "telefonla_konusma",
    "c3": "telefonla_konusma",
    "c4": "telefonla_konusma",
    "c6": "su_icme",
    "c7": "arkaya_bakma",
    "c8": "etrafa_bakinma",
    "c9": "etrafa_bakinma",
}

def process_single_image(row: dict, dataset_root: Path, output_root: Path, train_subjects: set) -> bool:
    class_id = row["classname"]
    # Skip classes that don't map to dangerous driver behaviors in FTR
    if class_id not in STATE_FARM_TO_FTR:
        return False
        
    ftr_label = STATE_FARM_TO_FTR[class_id]
    subject = row["subject"]
    img_name = row["img"]
    
    # Decide split based on subject to prevent data leakage (DS-009)
    split = "train" if subject in train_subjects else "val"
    
    src_path = dataset_root / "imgs" / "train" / class_id / img_name
    dest_path = output_root / split / ftr_label / f"{subject}_{img_name}"
    
    if not src_path.exists():
        return False
        
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Apply windshield simulation (80% probability to simulate glass, 20% keep original for augmentation)
    if random.random() < 0.8:
        WindshieldSimulator.transform_image(str(src_path), str(dest_path))
    else:
        shutil.copy(src_path, dest_path)
        
    return True

def main(max_samples: int = 2000):
    dataset_root = Path("data/datasets/state-farm-distracted-driver")
    output_root = Path("data/datasets/processed_state_farm")
    csv_path = dataset_root / "driver_imgs_list.csv"
    
    if not csv_path.exists():
        print(f"Error: State Farm csv not found at {csv_path}")
        return
        
    print(f"Loading metadata from {csv_path}...")
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["classname"] in STATE_FARM_TO_FTR:
                rows.append(row)
                
    # Group by subjects for splitting (DS-009)
    subjects = sorted(list(set(row["subject"] for row in rows)))
    random.seed(42)
    random.shuffle(subjects)
    
    # Split subjects 80% train, 20% validation
    split_idx = int(len(subjects) * 0.8)
    train_subjects = set(subjects[:split_idx])
    val_subjects = set(subjects[split_idx:])
    
    print(f"Subjects for Train ({len(train_subjects)}): {', '.join(train_subjects)}")
    print(f"Subjects for Val ({len(val_subjects)}): {', '.join(val_subjects)}")
    
    # Sample subset for fast trial-and-error if requested
    if max_samples and len(rows) > max_samples:
        print(f"Subsampling dataset to {max_samples} images for rapid trial-and-error...")
        rows = random.sample(rows, max_samples)
        
    print(f"Processing and augmenting {len(rows)} images using Windshield Simulator...")
    
    # Use ThreadPoolExecutor for fast parallel image preprocessing
    success_count = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(process_single_image, row, dataset_root, output_root, train_subjects)
            for row in rows
        ]
        for fut in futures:
            if fut.result():
                success_count += 1
                
    print(f"Preprocessing complete. Successfully processed {success_count} images under {output_root}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=2000, help="Max images to preprocess (0 for all)")
    args = parser.parse_args()
    
    main(max_samples=args.max_samples)
