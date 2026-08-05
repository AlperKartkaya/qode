import os
import sys
from huggingface_hub import HfApi, login

def upload_models(repo_id: str, token: str = None):
    if token:
        login(token=token)
        
    api = HfApi()
    
    # Ensure the repo exists (creates it if it doesn't)
    try:
        api.create_repo(repo_id=repo_id, exist_ok=True, repo_type="model")
        print(f"✅ Repository {repo_id} is ready.")
    except Exception as e:
        print(f"Could not create repo (it might already exist): {e}")

    models_to_upload = [
        ("data/weights/driver_classifier_finetuned.pt", "driver_classifier_finetuned.pt"),
        ("data/weights/smoker_classifier_finetuned.pt", "smoker_classifier_finetuned.pt"),
        ("data/weights/driver_classifier.pt", "driver_classifier.pt"),
        ("data/weights/smoker_classifier.pt", "smoker_classifier.pt")
    ]
    
    for local_path, path_in_repo in models_to_upload:
        if os.path.exists(local_path):
            print(f"Uploading {local_path}...")
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="model"
            )
            print(f"✅ Uploaded {path_in_repo} successfully!")
        else:
            print(f"⚠️ Skipping {local_path} (File not found)")
            
    print(f"\n🎉 All available models uploaded successfully to: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/upload_to_hf.py <HF_REPO_ID> [HF_TOKEN]")
        print("Example: python3 scripts/upload_to_hf.py QoDe-5G/qode-models")
        sys.exit(1)
        
    repo = sys.argv[1]
    hf_token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("HF_TOKEN")
    upload_models(repo, hf_token)
