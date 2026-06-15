#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Hugging Face libraries
from datasets import load_dataset
from huggingface_hub import login, HfApi

def upload_dataset(local_dir: str, repo_id: str):
    print(f"Uploading preprocessed {local_dir} to {repo_id}...")
    try:
        # Load dataset from the local ImageFolder structure
        dataset = load_dataset("imagefolder", data_dir=local_dir)
        # Push to hub
        dataset.push_to_hub(repo_id, private=False)
        print(f"Successfully uploaded to https://huggingface.co/datasets/{repo_id}")
    except Exception as e:
        print(f"Failed to upload {local_dir}: {e}")

def upload_raw_folder(local_dir: str, repo_id: str):
    print(f"Uploading RAW folder {local_dir} to {repo_id}...")
    api = HfApi()
    try:
        # Create repo if it doesn't exist
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
        # Upload the entire folder
        api.upload_folder(
            folder_path=local_dir,
            repo_id=repo_id,
            repo_type="dataset",
        )
        print(f"Successfully uploaded RAW folder to https://huggingface.co/datasets/{repo_id}")
    except Exception as e:
        print(f"Failed to upload RAW folder {local_dir}: {e}")

if __name__ == "__main__":
    # Load token from .env
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("Error: HF_TOKEN not found in .env file.")
        sys.exit(1)
        
    login(token=hf_token)
    
    # ── 1. Upload Clean / Processed Datasets ──
    driver_dir = "data/datasets/qode-driver-behaviors"
    if Path(driver_dir).exists():
        upload_dataset(driver_dir, "QoDe-5G/qode-driver-behaviors")
        
    vehicle_dir = "data/datasets/qode-vehicle-types"
    if Path(vehicle_dir).exists():
        upload_dataset(vehicle_dir, "QoDe-5G/qode-vehicle-types")

    # ── 2. Upload Raw Datasets (Just in Case) ──
    raw_datasets = {
        "data/datasets/advance-driver-monitoring-smartcity12": "QoDe-5G/raw-advance-driver-monitoring",
        "data/datasets/car-classification-iHasibi": "QoDe-5G/raw-car-classification-iHasibi",
        "data/datasets/vehicle-classification-marquis03": "QoDe-5G/raw-vehicle-classification-marquis03",
        "data/datasets/vehicle-type": "QoDe-5G/raw-vehicle-type",
    }
    
    for local_path, repo_name in raw_datasets.items():
        if Path(local_path).exists():
            upload_raw_folder(local_path, repo_name)

