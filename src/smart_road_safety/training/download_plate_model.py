import os
from huggingface_hub import hf_hub_download
import shutil
from pathlib import Path

def download_plate_model():
    weights_dir = Path("data/weights")
    weights_dir.mkdir(exist_ok=True, parents=True)
    
    print("YOLOv8 Plaka Bulucu modeli Hugging Face'ten indiriliyor...")
    try:
        # Downloading a popular license plate model from HF
        file_path = hf_hub_download(repo_id="keremberke/yolov8m-license-plate", filename="best.pt")
        dest_path = weights_dir / "license_plate_detector.pt"
        
        shutil.copy2(file_path, dest_path)
        print(f"Başarılı! Model şuraya kaydedildi: {dest_path}")
    except Exception as e:
        print(f"İndirme sırasında hata oluştu: {e}")

if __name__ == "__main__":
    download_plate_model()
