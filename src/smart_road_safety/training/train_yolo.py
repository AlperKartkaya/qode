import os
import yaml
from pathlib import Path

# Consolidate all FTR detection classes for YOLO object/vehicle detection
YOLO_CLASSES = {
    0: "sedan",
    1: "suv",
    2: "hatchback",
    3: "pickup",
    4: "minibus",
    5: "panelvan",
    6: "kamyon",
    7: "plaka",
    8: "teknocan",
    9: "bilgisayar",
    10: "on_koltuk",
    11: "arka_koltuk_1",
    12: "arka_koltuk_2"
}

def generate_dataset_yaml(dataset_dir: Path) -> Path:
    yaml_data = {
        "path": str(dataset_dir.absolute()),
        "train": "images/train",
        "val": "images/val",
        "names": YOLO_CLASSES
    }
    
    yaml_path = Path("data/custom_dataset.yaml")
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False)
        
    print(f"Generated YOLO dataset config at {yaml_path}")
    return yaml_path

def train_model(dataset_dir_str: str = "data/datasets/yolo_ftr_dataset"):
    dataset_dir = Path(dataset_dir_str)
    
    # 1. Generate YAML dataset configuration
    yaml_path = generate_dataset_yaml(dataset_dir)
    
    # 2. Check if yolo package is installed
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: 'ultralytics' (YOLO) is not installed. Install it using: pip install ultralytics")
        return
        
    print("Initializing YOLO11 small model pre-trained weights...")
    # Using 'yolo11s.pt' as a solid tradeoff between speed (T4 runtime) and accuracy
    model = YOLO("yolo11s.pt")
    
    print("Starting fine-tuning...")
    results = model.train(
        data=str(yaml_path),
        epochs=30,
        imgsz=640,
        batch=16,
        device=0,  # Run on GPU 0
        workers=4,
        project="qode-smart-road-safety",
        name="yolo11s-ftr-detect"
    )
    
    print(f"Training complete. Weights are saved in runs/detect/yolo11s-ftr-detect/weights/best.pt")

if __name__ == "__main__":
    # Create placeholder folder structure to allow validation run of the script
    Path("data/datasets/yolo_ftr_dataset/images/train").mkdir(parents=True, exist_ok=True)
    Path("data/datasets/yolo_ftr_dataset/images/val").mkdir(parents=True, exist_ok=True)
    
    # Run a dry check of YAML generation
    generate_dataset_yaml(Path("data/datasets/yolo_ftr_dataset"))
