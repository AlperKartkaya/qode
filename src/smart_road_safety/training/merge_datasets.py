import os
import shutil
from pathlib import Path

SOURCE_DIR = Path("data/training_data")
DEST_DIR = Path("data/datasets/qode-driver-behaviors/train")

def merge_datasets():
    if not SOURCE_DIR.exists() or not DEST_DIR.exists():
        print("Kaynak veya hedef dizin bulunamadı!")
        return
        
    for category_dir in SOURCE_DIR.iterdir():
        if not category_dir.is_dir():
            continue
            
        category_name = category_dir.name
        dest_category_dir = DEST_DIR / category_name
        dest_category_dir.mkdir(exist_ok=True, parents=True)
        
        copied = 0
        for img_path in category_dir.glob("*.jpg"):
            dest_img_path = dest_category_dir / img_path.name
            if not dest_img_path.exists():
                shutil.copy2(img_path, dest_img_path)
                copied += 1
                
        print(f"[{category_name}] {copied} yeni fotoğraf State Farm Master veri setine kopyalandı.")

if __name__ == "__main__":
    print("Veri birleştirme başlıyor...")
    merge_datasets()
    print("Bitti! Artık devasa bir FTR veri setimiz var.")
