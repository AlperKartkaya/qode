import os
import shutil
import random
from pathlib import Path
from ultralytics import YOLO

# Yollar
BASE_DIR = Path("data/datasets/tr-licence-plates")
IMAGES_DIR = BASE_DIR / "images"

# YOLO formatı için hedef klasörler
YOLO_DIR = Path("data/datasets/yolo_plate_dataset")
TRAIN_IMG = YOLO_DIR / "train" / "images"
TRAIN_LBL = YOLO_DIR / "train" / "labels"
VAL_IMG = YOLO_DIR / "val" / "images"
VAL_LBL = YOLO_DIR / "val" / "labels"

def prepare_dataset():
    print("Veri seti YOLO formatına uygun hale getiriliyor...")
    # Klasörleri oluştur
    for d in [TRAIN_IMG, TRAIN_LBL, VAL_IMG, VAL_LBL]:
        d.mkdir(parents=True, exist_ok=True)
        
    # Tüm .jpg dosyalarını bul
    all_images = list(IMAGES_DIR.glob("*.jpg"))
    random.shuffle(all_images)
    
    # %80 Train, %20 Validation
    split_idx = int(len(all_images) * 0.8)
    train_imgs = all_images[:split_idx]
    val_imgs = all_images[split_idx:]
    
    def copy_files(img_list, img_dest, lbl_dest):
        for img_path in img_list:
            # Resim kopyala
            shutil.copy2(img_path, img_dest / img_path.name)
            
            # Etiket kopyala (Aynı klasörde .txt var)
            txt_path = img_path.with_suffix(".txt")
            if txt_path.exists():
                shutil.copy2(txt_path, lbl_dest / txt_path.name)
            else:
                # Bazen etiketler label klasöründe olabiliyor
                alt_txt_path = BASE_DIR / "label" / txt_path.name
                if alt_txt_path.exists():
                    shutil.copy2(alt_txt_path, lbl_dest / txt_path.name)

    print(f"Eğitim için {len(train_imgs)} resim kopyalanıyor...")
    copy_files(train_imgs, TRAIN_IMG, TRAIN_LBL)
    
    print(f"Doğrulama için {len(val_imgs)} resim kopyalanıyor...")
    copy_files(val_imgs, VAL_IMG, VAL_LBL)
    
    # dataset.yaml oluştur
    yaml_content = f"""
path: {YOLO_DIR.absolute()}
train: train/images
val: val/images

names:
  0: plaka
"""
    yaml_path = YOLO_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
        
    print(f"dataset.yaml şuraya oluşturuldu: {yaml_path}")
    return yaml_path

def train_plate_detector():
    yaml_path = prepare_dataset()
    print("YOLOv11 Nano modeli ile plaka eğitimi başlıyor...")
    
    model = YOLO("yolo11n.pt")
    model.train(
        data=str(yaml_path),
        epochs=10,  # Hızlı eğitim için 10 epoch
        imgsz=640,
        device="mps",
        project="data/weights/runs",
        name="plate_detector",
        exist_ok=True
    )
    
    # En iyi modeli asıl weights klasörüne kopyala
    best_model_path = Path("data/weights/runs/plate_detector/weights/best.pt")
    dest_model_path = Path("data/weights/license_plate_detector.pt")
    
    if best_model_path.exists():
        shutil.copy2(best_model_path, dest_model_path)
        print(f"Başarılı! Model şuraya kopyalandı: {dest_model_path}")

if __name__ == "__main__":
    train_plate_detector()
