"""
Fine-tuning script for TEKNOFEST 2026 Phase 2.
This script extracts frames from the Phase 2 video and matches them with faz2_gt.json
to create a fine-tuning dataset for YOLO and EfficientNet.
"""
import json
import os
import cv2
from pathlib import Path

def create_finetuning_dataset(video_path: str, gt_path: str, output_dir: str):
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
    
    extracted = 0
    frame_idx = 0
    while True:
        ret, frame = video.read()
        if not ret:
            break
            
        if frame_idx in events_by_frame:
            # Save frame
            frame_filename = f"frame_{frame_idx}.jpg"
            frame_path = os.path.join(images_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            
            # Save labels (placeholder bounding boxes for YOLO format)
            # Note: The JSON only gives temporal labels, so spatial bounding boxes
            # would need to be manually annotated or pseudo-labeled.
            label_path = os.path.join(labels_dir, f"frame_{frame_idx}.txt")
            with open(label_path, "w") as lf:
                for ev in events_by_frame[frame_idx]:
                    # Writing category and label as text for classification fine-tuning
                    lf.write(f"{ev['kategori']},{ev['etiket']}\n")
            
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
    parser.add_argument("--gt", type=str, default="faz2_gt (1).json", help="Path to JSON GT")
    parser.add_argument("--out", type=str, default="data/finetune", help="Output directory")
    args = parser.parse_args()
    
    create_finetuning_dataset(args.video, args.gt, args.out)
