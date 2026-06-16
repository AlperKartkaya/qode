import cv2
import os
from pathlib import Path

INPUT_DIR = Path("data/datasets/smoking")
OUTPUT_DIR = Path("data/training_data/sigara_icme")

def extract_smoking_videos():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sadece doğrudan smoking klasöründeki mp4 dosyalarını bul
    video_files = [f for f in INPUT_DIR.glob("*.mp4")]
    
    if not video_files:
        print("MP4 dosyası bulunamadı.")
        return
        
    print(f"{len(video_files)} adet video bulundu. Kare çıkarma başlıyor...")
    
    for video_file in video_files:
        cap = cv2.VideoCapture(str(video_file))
        fps = int(cap.get(cv2.CAP_PROP_FPS) or 25)
        
        frame_idx = 0
        saved_count = 0
        base_name = video_file.stem.replace(" ", "_")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Saniyede 1 kare (veya fps/2 kare) alalım
            if frame_idx % fps == 0:
                out_filename = OUTPUT_DIR / f"{base_name}_frame_{frame_idx}.jpg"
                cv2.imwrite(str(out_filename), frame)
                saved_count += 1
                
            frame_idx += 1
            
        cap.release()
        print(f"{video_file.name} tamamlandı. {saved_count} kare çıkarıldı.")

if __name__ == "__main__":
    extract_smoking_videos()
    print("İşlem bitti! Fotoğraflar data/training_data/sigara_icme klasöründe.")
