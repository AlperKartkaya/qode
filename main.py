import os
import json
from pathlib import Path
import sys

# Ensure src is in path if not already
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_road_safety.analysis import AnalysisSessionRequest, AnalyzerInput, run_analysis_session
from smart_road_safety.competition.ftr import build_ftr_result_from_analysis, write_ftr_result, VehicleInfo

def main() -> None:
    input_dir = Path("/app/data/input")
    output_dir = Path("/app/data/output")
    
    try:
        # Ensure dirs exist for local testing
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass # Probably not running in docker and /app is read-only on mac
    
    video_files = list(input_dir.glob("*.mp4"))
    if not video_files:
        print("No mp4 file found in /app/data/input")
        # For testing without docker, let's look locally
        video_files = list(Path(".").glob("*.mp4"))
        if not video_files:
            print("No mp4 file found locally either. Create a dummy one for testing.")
            return
        video_path = video_files[0]
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)
    else:
        video_path = video_files[0]
    
    print(f"Processing video: {video_path}")
    
    # Run analysis (Placeholder logic as per current state)
    request = AnalysisSessionRequest(
        session_id="ftr-session",
        phone_number="+905551112233",
        device_session_id="ftr-device",
        requested_profile="standard",
        verification_should_pass=True,
        qod_should_allow_boost=True,
        analyzer_input=AnalyzerInput(
            source_ref=str(video_path),
            quality_profile="standard",
            target_vehicle_confidence=0.9,
            plate_visibility_score=0.9,
            driver_risk_score=0.8,
            distance_meters=10.0,
            driver_risk_label="smoking", # Maps to "sigara_icme" in FTR
        )
    )
    result = run_analysis_session(request)
    
    # Map to FTR structure using the established architecture
    ftr_result = build_ftr_result_from_analysis(
        analysis_result=result.analysis_result,
        video_id=video_path.name,
        vehicle_info=VehicleInfo(
            tip="sedan",
            plaka="34ABC123",
            renk="beyaz",
            confidence_score=0.95,
        ),
        event_time_seconds=1.5
    )
    
    out_file = output_dir / "results.json"
    write_ftr_result(ftr_result, out_file)
    print(f"FTR Output saved to {out_file}")

if __name__ == "__main__":
    main()
