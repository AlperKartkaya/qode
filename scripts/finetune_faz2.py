"""
Fine-tuning script for TEKNOFEST 2026 Phase 2.
This script extracts event frames for classification calibration. The Faz 2 clip
must not also be used for a reported holdout metric; see the final-stage manifest.
"""
import json
import os
import cv2
from pathlib import Path

def create_finetuning_dataset(
    video_path: str, gt_path: str, output_dir: str, safe_interval_seconds: float = 2.0
):
    print(f"Loading GT from {gt_path}...")
    with open(gt_path, "r") as f:
        gt_data = json.load(f)

    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps = video.get(cv2.CAP_PROP_FPS)
    print(f"Video FPS: {fps}")

    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    # Dictionary of events by frame number
    events_by_frame = {}
    for event in gt_data.get("tespitler", []):
        time_sec = float(event["zaman_saniye"])
        frame_num = int(time_sec * fps)
        
        if frame_num not in events_by_frame:
            events_by_frame[frame_num] = []
        events_by_frame[frame_num].append(event)

    print(f"Found {len(events_by_frame)} unique frames with events to extract.")
    driver_event_frames = sorted(
        frame_num for frame_num, events in events_by_frame.items()
        if any(event.get("kategori") == "sofor_eylemi" for event in events)
    )
    safe_step = max(1, int(safe_interval_seconds * fps))
    exclusion = max(1, int(fps))
    safe_frames = {
        frame_num for frame_num in range(0, int(video.get(cv2.CAP_PROP_FRAME_COUNT)), safe_step)
        if all(abs(frame_num - event_frame) > exclusion for event_frame in driver_event_frames)
    }
    
    extracted = 0
    frame_idx = 0
    while True:
        ret, frame = video.read()
        if not ret:
            break
            
        if frame_idx in events_by_frame or frame_idx in safe_frames:
            # Save frame
            frame_filename = f"frame_{frame_idx}.jpg"
            frame_path = os.path.join(images_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            
            # The GT has temporal class labels, not spatial bounding boxes. These
            # CSV-like rows are classification calibration labels and must never be
            # presented as YOLO detection annotations.
            label_path = os.path.join(labels_dir, f"frame_{frame_idx}.txt")
            with open(label_path, "w") as lf:
                for ev in events_by_frame.get(frame_idx, []):
                    # Writing category and label as text for classification fine-tuning
                    lf.write(f"{ev['kategori']},{ev['etiket']}\n")
                if frame_idx in safe_frames:
                    lf.write("sofor_eylemi,safe_driving\n")
            
            extracted += 1
            
        frame_idx += 1

    video.release()
    print(f"Extraction complete! Extracted {extracted} frames to {output_dir}")
    print("Next step: Use these frames to pseudo-label bounding boxes for YOLO,")
    print("or use them directly to fine-tune the EfficientNet driver classifier.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract fine-tuning data from Phase 2 GT")
    parser.add_argument("--video", type=str, required=True, help="Path to faz2.mp4")
    parser.add_argument(
        "--gt",
        type=str,
        default="data/final_stage/faz2/ground_truth.json",
        help="Path to the canonical development-only FTR ground truth",
    )
    parser.add_argument("--out", type=str, default="data/finetune", help="Output directory")
    parser.add_argument(
        "--safe-interval-seconds", type=float, default=2.0,
        help="Sample safe-driving negatives this often, excluding one second around events",
    )
    args = parser.parse_args()
    
    create_finetuning_dataset(args.video, args.gt, args.out, args.safe_interval_seconds)
