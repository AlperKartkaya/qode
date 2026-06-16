from ultralytics import YOLO
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=50)
    args = parser.parse_args()

    # Load YOLOv11 nano model (super lightweight)
    print("[TeknocanTrain] Yükleniyor: yolo11n.pt")
    model = YOLO("yolo11n.pt")
    
    data_yaml_path = Path("data/datasets/teknocan_augmented/data.yaml").absolute()
    
    print(f"[TeknocanTrain] Eğitim Başlıyor... Epochs: {args.epochs}")
    results = model.train(
        data=str(data_yaml_path),
        epochs=args.epochs,
        imgsz=640,
        device="mps",  # or "cuda" / "cpu" if running elsewhere
        batch=16,
        project="data/weights",
        name="teknocan_run",
        exist_ok=True
    )
    
    print("[TeknocanTrain] Eğitim Tamamlandı!")
    
    # Move the best weights to the root of data/weights for easy access
    best_weights = Path("data/weights/teknocan_run/weights/best.pt")
    if best_weights.exists():
        import shutil
        shutil.copy(best_weights, "data/weights/teknocan_detector.pt")
        print("[TeknocanTrain] En iyi model data/weights/teknocan_detector.pt olarak kopyalandı.")

if __name__ == "__main__":
    main()
