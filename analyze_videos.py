import sys
import json
import cv2
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from smart_road_safety.analysis.model_inference import SceneAnalysisEngine
from main import _build_inferred_vehicle_info, _deduplicate_events
from smart_road_safety.competition.ftr import FtrCompetitionResult, write_ftr_result

def process_video(video_path: Path):
    print(f"\n--- Processing {video_path.name} ---")
    
    engine = SceneAnalysisEngine()
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error opening video stream or file {video_path}")
        return
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30
    
    vehicle_types = []
    vehicle_colors = []
    vehicle_scores = []
    plate_votes = {}
    raw_events = []
    
    vehicle_x_centers = []
    
    frame_count = 0
    # Process 1 frame every 1 second
    frames_to_skip = int(fps)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frames_to_skip == 0:
            timestamp_sec = frame_count / fps
            # Skip first 1-2 seconds if needed, but let's process all sampled frames
            analysis = engine.analyze_frame(frame, timestamp_sec)
            
            if analysis.get("vehicle_detected"):
                vehicle_types.append(str(analysis["vehicle_type"]))
                vehicle_colors.append(str(analysis["vehicle_color"]))
                vehicle_scores.append(float(analysis["vehicle_confidence"]))
                
                # Slalom takibi için X merkezini kaydet
                vbox = analysis.get("vehicle_box")
                if vbox:
                    x1, y1, x2, y2 = vbox
                    vehicle_x_centers.append((x1 + x2) / 2.0)
                else:
                    vehicle_x_centers.append(vehicle_x_centers[-1] if vehicle_x_centers else 0)

                plate = analysis.get("plate_text")
                if isinstance(plate, str) and plate.strip():
                    plate_votes[plate] = plate_votes.get(plate, 0) + 1
                    
            for event in analysis.get("driver_events", []):
                if float(event.get("confidence_score", 0.0)) >= 0.55:
                    raw_events.append(dict(event))
                    
        frame_count += 1
        
    cap.release()
    
    # ── Slalom (Tehlikeli Şerit Değiştirme) Analizi ──
    if len(vehicle_x_centers) >= 3:
        smoothed = [sum(vehicle_x_centers[i:i+3])/len(vehicle_x_centers[i:i+3]) for i in range(len(vehicle_x_centers)-2)]
        directions = []
        current_dir = 0
        for i in range(1, len(smoothed)):
            diff = smoothed[i] - smoothed[i-1]
            if diff > 5: # Sağa kaydı
                if current_dir != 1:
                    directions.append(1)
                    current_dir = 1
            elif diff < -5: # Sola kaydı
                if current_dir != -1:
                    directions.append(-1)
                    current_dir = -1
        
        # Eğer en az 2 yön değişimi varsa (Örn: Sol -> Sağ) slalom yapıyordur
        if len(directions) >= 2:
            raw_events.append({
                "zaman_saniye": 0.0,
                "kategori": "sofor_eylemi",
                "etiket": "slalom",
                "confidence_score": 0.95
            })

    events = _deduplicate_events(raw_events)
    vehicle_info = _build_inferred_vehicle_info(vehicle_types, vehicle_colors, vehicle_scores, plate_votes)
    
    if vehicle_info:
        ftr_result = FtrCompetitionResult(
            video_id=video_path.name,
            arac_bilgisi=vehicle_info,
            tespitler=tuple(events),
        )
        out_path = Path(f"out/results_{video_path.stem}.json")
        out_path.parent.mkdir(exist_ok=True)
        write_ftr_result(ftr_result, out_path)
        
        with open(out_path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"No vehicle detected in {video_path.name}.")

if __name__ == "__main__":
    video_dir = Path("data/test-videos")
    if not video_dir.exists():
        print(f"Directory {video_dir} not found.")
        sys.exit(1)
        
    for v in sorted(video_dir.glob("*")):
        if v.suffix in [".mp4", ".mov", ".avi"] or v.name == "video_1":
            process_video(v)
