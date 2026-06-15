"""
preprocess_state_farm.py — State Farm Dataset Preprocessor

Maps State Farm c0-c9 classes to FTR labels, applies Windshield Simulator
augmentation, and organises images into train/ val/ folders for ImageFolder loading.

Subject-level split (DS-009): all images of a given driver go to the same split
to prevent data leakage between train and validation sets.

Usage:
    # Full dataset (~22k FTR-relevant images, ~10-15 min on M4 Pro):
    python -m smart_road_safety.training.preprocess_state_farm --max-samples 0

    # Quick trial (~2000 images):
    python -m smart_road_safety.training.preprocess_state_farm --max-samples 2000
"""

import csv
import os
import random
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .windshield_simulator import WindshieldSimulator

# ── FTR label mapping ─────────────────────────────────────────────────────────
# State Farm class → FTR sofor_eylemi label  (None = safe driving, skip it)
STATE_FARM_TO_FTR: dict[str, str | None] = {
    "c0": None,                      # safe_driving  — excluded
    "c1": "telefonla_konusma",       # texting_right
    "c2": "telefonla_konusma",       # phone_right
    "c3": "telefonla_konusma",       # texting_left
    "c4": "telefonla_konusma",       # phone_left
    "c5": "etrafa_bakinma",          # operating_radio
    "c6": "su_icme",                 # drinking
    "c7": "arkaya_bakma",            # reaching_behind
    "c8": "etrafa_bakinma",          # hair_and_makeup
    "c9": "etrafa_bakinma",          # talking_to_passenger
}

# All FTR sofor_eylemi labels we plan to classify
ALL_FTR_LABELS = [
    "arkaya_bakma",
    "etrafa_bakinma",
    "su_icme",
    "telefonla_konusma",
    # Note: esneme, sigara_icme, emniyet_kemeri_ihlali, slalom not in State Farm;
    # they come from DMD / DriverSVT datasets and are handled by the YOLO pipeline.
]


def _process_image(
    row: dict,
    dataset_root: Path,
    output_root: Path,
    train_subjects: set[str],
) -> bool:
    """Copy (and optionally augment) a single image to the processed folder."""
    cls_id = row["classname"]
    ftr_label = STATE_FARM_TO_FTR.get(cls_id)
    if ftr_label is None:
        return False  # Safe driving or unmapped class

    subject  = row["subject"]
    img_name = row["img"]
    split    = "train" if subject in train_subjects else "val"

    src  = dataset_root / "imgs" / "train" / cls_id / img_name
    dest = output_root / split / ftr_label / f"{subject}_{img_name}"

    if not src.exists():
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Apply windshield simulation to ~80% of images for domain adaptation;
    # keep 20% unaugmented to preserve original distribution.
    if random.random() < 0.80:
        WindshieldSimulator.transform_image(str(src), str(dest))
    else:
        shutil.copy(src, dest)

    return True


def main(max_samples: int = 0) -> None:
    """
    Args:
        max_samples: Maximum images to process.  0 = use all available images.
    """
    dataset_root = Path("data/datasets/state-farm-distracted-driver")
    output_root  = Path("data/datasets/processed_state_farm")
    csv_path     = dataset_root / "driver_imgs_list.csv"

    if not csv_path.exists():
        print(f"[Preprocess] ERROR: State Farm CSV not found at {csv_path}")
        print("             Download the dataset from Kaggle first.")
        return

    print(f"[Preprocess] Loading metadata from {csv_path}…")
    rows: list[dict] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if STATE_FARM_TO_FTR.get(row["classname"]) is not None:
                rows.append(row)

    print(f"[Preprocess] FTR-relevant images found: {len(rows)}")

    # Subject-level split — all frames of a subject go to the same set (DS-009)
    subjects = sorted(set(r["subject"] for r in rows))
    random.seed(42)
    random.shuffle(subjects)
    split_idx      = int(len(subjects) * 0.80)
    train_subjects = set(subjects[:split_idx])
    val_subjects   = set(subjects[split_idx:])

    print(f"[Preprocess] Subjects  train={len(train_subjects)}  val={len(val_subjects)}")
    print(f"[Preprocess] Train subjects: {', '.join(sorted(train_subjects))}")
    print(f"[Preprocess] Val   subjects: {', '.join(sorted(val_subjects))}")

    if max_samples and len(rows) > max_samples:
        print(f"[Preprocess] Subsampling to {max_samples} images (trial mode)…")
        rows = random.sample(rows, max_samples)

    print(f"[Preprocess] Processing {len(rows)} images with up to 8 parallel workers…")

    # Ensure output label folders exist
    for label in ALL_FTR_LABELS:
        for split in ("train", "val"):
            (output_root / split / label).mkdir(parents=True, exist_ok=True)

    success = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_process_image, row, dataset_root, output_root, train_subjects): row
            for row in rows
        }
        for i, fut in enumerate(as_completed(futures), 1):
            if fut.result():
                success += 1
            if i % 1000 == 0:
                print(f"[Preprocess]   {i}/{len(rows)} processed…")

    print(f"[Preprocess] Done.  {success}/{len(rows)} images written to {output_root}")

    # Print per-class counts for verification
    for split in ("train", "val"):
        for label in ALL_FTR_LABELS:
            count = len(list((output_root / split / label).glob("*.jpg")))
            print(f"  {split:5s}/{label}: {count}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Preprocess State Farm dataset for FTR training")
    p.add_argument("--max-samples", type=int, default=0,
                   help="Max images to process (0 = all, ~22k)")
    args = p.parse_args()
    main(max_samples=args.max_samples)
