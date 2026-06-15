import os
import zipfile
import shutil
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("Error: 'huggingface_hub' is not installed. Install it using: pip install huggingface_hub")
    exit(1)

def main():
    # Read Hugging Face token from .env
    token = None
    env_path = Path(".env")
    if env_path.exists():
        with env_path.open("r") as f:
            for line in f:
                if line.startswith("HF_TOKEN="):
                    token = line.split("=")[1].strip()

    if token:
        os.environ["HF_TOKEN"] = token
        print("HF_TOKEN loaded from .env file.")
    else:
        print("Warning: HF_TOKEN not found in .env. Will attempt public download.")

    dataset_root_dir = Path("data/datasets")
    dataset_root_dir.mkdir(parents=True, exist_ok=True)

    def download_and_extract_zip(repo_id: str, filename: str, target_dir: Path):
        print(f"\n--- Downloading {filename} from {repo_id} ---")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            downloaded_file = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                repo_type="dataset",
                token=token
            )
            print(f"Downloaded to cache: {downloaded_file}")
            
            # Extract zip file
            print(f"Extracting to {target_dir}...")
            with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            print(f"Extraction complete for {filename}.")
        except Exception as e:
            print(f"Error processing {repo_id}: {e}")

    def download_file_direct(repo_id: str, filename: str, target_dir: Path):
        print(f"\n--- Downloading {filename} from {repo_id} ---")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            downloaded_file = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                repo_type="dataset",
                token=token
            )
            print(f"Downloaded to cache: {downloaded_file}")
            
            # Copy to destination
            dest_file = target_dir / filename
            print(f"Copying to {dest_file}...")
            shutil.copy(downloaded_file, dest_file)
            print(f"Copy complete for {filename}.")
        except Exception as e:
            print(f"Error processing {repo_id}: {e}")

    # 1. State Farm
    download_and_extract_zip(
        repo_id="QoDe-5G/state-farm-distracted-driver",
        filename="state-farm-distracted-driver-detection.zip",
        target_dir=dataset_root_dir / "state-farm-distracted-driver"
    )

    # 2. DMD Drowsiness
    download_and_extract_zip(
        repo_id="QoDe-5G/dmd-drowsiness",
        filename="dmd-drowsiness.zip",
        target_dir=dataset_root_dir / "dmd-drowsiness"
    )

    # 3. DMD Distraction
    download_and_extract_zip(
        repo_id="QoDe-5G/dmd-distraction",
        filename="dmd-distraction.zip",
        target_dir=dataset_root_dir / "dmd-distraction"
    )

    # 4. DriverSVT
    download_file_direct(
        repo_id="QoDe-5G/DriverSVT-teknofest",
        filename="DriverSVT.csv",
        target_dir=dataset_root_dir / "DriverSVT-teknofest"
    )

    print("\n--- All Dataset Ingestions Complete ---")

if __name__ == "__main__":
    main()
