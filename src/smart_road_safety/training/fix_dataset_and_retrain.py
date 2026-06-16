import os
import shutil
from pathlib import Path

BAD_DIR = Path("data/training_data/sigara_icme")
GOOD_DIR = Path("data/datasets/smoking/smoker-detection/Training/Training")
MASTER_DIR = Path("data/datasets/qode-driver-behaviors/train/sigara_icme")

def fix_dataset():
    print("1. Ezberlemeye (Overfitting) neden olan kötü stok video fotoğraflarını siliyoruz...")
    # Remove the bad images we copied today
    deleted = 0
    if BAD_DIR.exists():
        for img in BAD_DIR.glob("*.jpg"):
            target = MASTER_DIR / img.name
            if target.exists():
                target.unlink()
                deleted += 1
    print(f"Toplam {deleted} adet kötü/ezberleten fotoğraf silindi.")

    print("2. Onun yerine 700+ adet jenerik 'Smoker Detection' verisini ekliyoruz...")
    added = 0
    if GOOD_DIR.exists():
        for img in GOOD_DIR.glob("smoking_*.jpg"):
            target = MASTER_DIR / img.name
            if not target.exists():
                shutil.copy2(img, target)
                added += 1
    print(f"Toplam {added} adet taze, farklı insanlardan oluşan sigara fotoğrafı eklendi.")

if __name__ == "__main__":
    fix_dataset()
    print("Veri seti onarıldı! Şimdi tekrar eğitime hazır.")
