import os
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# FTR allowed categories and labels
FTR_TAXONOMY = {
    "sofor_eylemi": [
        "arkaya_bakma",
        "esneme",
        "sigara_icme",
        "su_icme",
        "telefonla_konusma",
        "slalom",
        "etrafa_bakinma",
        "emniyet_kemeri_ihlali",
    ],
    "nesneler": ["teknocan", "bilgisayar"],
    "yolcular": ["arka_koltuk_1", "arka_koltuk_2", "on_koltuk"],
}

# Mapping configs for support datasets
STATE_FARM_MAP = {
    "safe_driving": None,  # Not mapped to dangerous actions
    "texting_right": "telefonla_konusma",
    "phone_right": "telefonla_konusma",
    "texting_left": "telefonla_konusma",
    "phone_left": "telefonla_konusma",
    "operating_radio": "etrafa_bakinma",
    "drinking": "su_icme",
    "reaching_behind": "arkaya_bakma",
    "hair_and_makeup": "etrafa_bakinma",
    "talking_to_passenger": "etrafa_bakinma",
}

DMD_MAP = {
    "texting_left": "telefonla_konusma",
    "texting_right": "telefonla_konusma",
    "phonecall_left": "telefonla_konusma",
    "phonecall_right": "telefonla_konusma",
    "drinking": "su_icme",
    "reach_backseat": "arkaya_bakma",
    "reach_side": "etrafa_bakinma",
    "hair_and_makeup": "etrafa_bakinma",
    "operating_radio": "etrafa_bakinma",
    "talking_to_passenger": "etrafa_bakinma",
    "yawning_with_hand": "esneme",
    "yawning_without_hand": "esneme",
    "safe_drive": None,
}

DRIVER_SVT_MAP = {
    "Normal": None,
    "Camera off": None,
    "Distraction": "etrafa_bakinma",
    "Unfastened belt": "emniyet_kemeri_ihlali",
    "Drowsiness": "esneme",
    "No attention": "etrafa_bakinma",
    "Using phone": "telefonla_konusma",
    "Eating": "su_icme",
    "Smoking": "sigara_icme",
}

def map_state_farm_label(label: str) -> str | None:
    return STATE_FARM_MAP.get(label)

def map_dmd_label(label: str) -> str | None:
    return DMD_MAP.get(label)

def map_driver_svt_label(label: str) -> str | None:
    return DRIVER_SVT_MAP.get(label)

def get_ftr_label_to_index() -> Dict[str, int]:
    # Returns a mapping from label name to a numeric index for multi-class classification
    all_labels = []
    for category, labels in FTR_TAXONOMY.items():
        all_labels.extend(labels)
    return {label: i for i, label in enumerate(all_labels)}

def export_classification_dataset(dataset_name: str, inventory: Any, output_dir: Path) -> None:
    """Helper function to organize dataset images into FTR label folders for PyTorch/YOLO training."""
    print(f"Exporting {dataset_name} to FTR folders in {output_dir}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create class subdirectories
    for label in FTR_TAXONOMY["sofor_eylemi"]:
        (output_dir / label).mkdir(exist_ok=True)
    
    # Process inventory
    count = 0
    if dataset_name == "state_farm":
        for s in inventory.train_samples:
            ftr_label = map_state_farm_label(s.class_name)
            if ftr_label:
                src_path = Path(s.image_path)
                if src_path.exists():
                    dest_path = output_dir / ftr_label / src_path.name
                    if not dest_path.exists():
                        import shutil
                        shutil.copy(src_path, dest_path)
                        count += 1
                        
    print(f"Exported {count} samples successfully.")

if __name__ == "__main__":
    print("FTR Label Taxonomy:")
    for cat, labels in FTR_TAXONOMY.items():
        print(f"  {cat}: {', '.join(labels)}")
