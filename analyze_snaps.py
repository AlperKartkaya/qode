import sys
import json
import cv2
from pathlib import Path

# Add src to pythonpath so imports work
sys.path.insert(0, str(Path("src").resolve()))

from smart_road_safety.analysis.model_inference import SceneAnalysisEngine
from main import _build_inferred_vehicle_info, _deduplicate_events
from smart_road_safety.competition.ftr import FtrCompetitionResult, write_ftr_result

def process_snaps(folder_name):
    folder_path = Path("data") / folder_name
    if not folder_path.exists():
        return
        
    print(f"\n--- Processing {folder_name} ---")
    
    engine = SceneAnalysisEngine()
    
    vehicle_types = []
    vehicle_colors = []
    vehicle_scores = []
    plate_votes = {}
    raw_events = []
    
    # Sort files so timestamps are sequential
    image_files = sorted([p for p in folder_path.glob("*.png")])
    if not image_files:
        print(f"No images found in {folder_name}")
        return
        
    for i, img_path in enumerate(image_files):
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
            
        timestamp = float(i) # treat each image as 1 second apart
        analysis = engine.analyze_frame(frame, timestamp)
        
        if analysis.get("vehicle_detected"):
            vehicle_types.append(str(analysis["vehicle_type"]))
            vehicle_colors.append(str(analysis["vehicle_color"]))
            vehicle_scores.append(float(analysis["vehicle_confidence"]))
            plate = analysis.get("plate_text")
            if isinstance(plate, str) and plate.strip():
                plate_votes[plate] = plate_votes.get(plate, 0) + 1
                
        for event in analysis.get("driver_events", []):
            if float(event.get("confidence_score", 0.0)) >= 0.55:
                raw_events.append(dict(event))

    events = _deduplicate_events(raw_events)
    vehicle_info = _build_inferred_vehicle_info(vehicle_types, vehicle_colors, vehicle_scores, plate_votes)
    
    # Generate JSON
    if vehicle_info:
        ftr_result = FtrCompetitionResult(
            video_id=f"{folder_name}.mp4",
            arac_bilgisi=vehicle_info,
            tespitler=tuple(events),
        )
        out_path = Path(f"out/results_{folder_name}.json")
        out_path.parent.mkdir(exist_ok=True)
        write_ftr_result(ftr_result, out_path)
        
        # Read the file and print it
        with open(out_path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"No vehicle detected in {folder_name}.")

process_snaps("snap_from_video_1")
process_snaps("snap_from_video_2")
process_snaps("snap_from_video_3")
