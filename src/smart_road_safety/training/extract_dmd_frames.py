import cv2
import json
import os
from pathlib import Path

# Eşleştirmek istediğimiz DMD etiketleri -> FTR etiketleri
LABEL_MAP = {
    'driver_actions/drinking': 'su_icme',
    'driver_actions/reach_side': 'etrafa_bakinma',
    'yawning/Yawning with hand': 'esneme',
    'yawning/Yawning without hand': 'esneme',
    'talking/talking': 'telefonla_konusma', # DMD'de telefonda konuşma ise (Bazen sadece konuşma olabilir, manuel kontrol gerekir)
    'driver_actions/safe_drive': 'safe_driving'
}

OUTPUT_DIR = Path("data/training_data")

def extract_from_dmd(dataset_path):
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        return
        
    print(f"Tarama başlatılıyor: {dataset_path}")
    
    for video_file in dataset_path.rglob("*_face.mp4"):
        # İlgili JSON dosyasını bul (video adı ile aynı prefix)
        base_name = video_file.name.replace("_face.mp4", "")
        # JSON dosyasının isminde genellikle _ann_distraction veya _ann_drowsiness olur
        json_files = list(video_file.parent.glob(f"{base_name}*ann*.json"))
        
        if not json_files:
            continue
            
        json_file = json_files[0]
        with open(json_file, 'r') as f:
            data = json.load(f)
            
        # Action ID'lerin hangi string türe ait olduğunu çıkar
        actions_dict = data.get("openlabel", {}).get("actions", {})
        action_id_to_type = {aid: info.get("type") for aid, info in actions_dict.items()}
        
        frames_info = data.get("openlabel", {}).get("frames", {})
        
        cap = cv2.VideoCapture(str(video_file))
        fps = int(cap.get(cv2.CAP_PROP_FPS) or 25)
        
        frame_idx = 0
        saved_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Saniyede sadece 1 veya 2 kare alalım ki yüzbinlerce aynı fotoğraf olmasın
            if frame_idx % (fps // 2) == 0:
                frame_data = frames_info.get(str(frame_idx), {})
                active_actions = frame_data.get("actions", {})
                
                # Bu karede çalan tüm etiketleri kontrol et
                for aid in active_actions.keys():
                    dmd_action_type = action_id_to_type.get(aid)
                    if dmd_action_type in LABEL_MAP:
                        ftr_label = LABEL_MAP[dmd_action_type]
                        
                        out_folder = OUTPUT_DIR / ftr_label
                        out_folder.mkdir(parents=True, exist_ok=True)
                        
                        out_filename = out_folder / f"{base_name}_frame_{frame_idx}.jpg"
                        cv2.imwrite(str(out_filename), frame)
                        saved_count += 1
                        break # Bir etiket yeterli
            frame_idx += 1
            
        cap.release()
        print(f"{video_file.name} tamamlandı. {saved_count} faydalı kare çıkarıldı.")

if __name__ == "__main__":
    extract_from_dmd("data/datasets/dmd-distraction")
    extract_from_dmd("data/datasets/dmd-drowsiness")
    print("İşlem bitti! Fotoğraflar data/training_data klasöründe.")
