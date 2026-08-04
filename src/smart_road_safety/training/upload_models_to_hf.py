import os
import json
from pathlib import Path
from huggingface_hub import HfApi

# Repoyu QoDe-5G organizasyonunda oluşturuyoruz
REPO_ID = "QoDe-5G/qode-models"
WEIGHTS_DIR = Path("data/weights")
MANIFEST_PATH = Path("config/runtime_assets.json")


def models_to_upload() -> list[str]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [
        asset["filename"] for asset in payload["assets"]
        if asset.get("source", "").startswith("https://huggingface.co/QoDe-5G/qode-models")
    ]

def upload_to_hf():
    api = HfApi()
    
    # Repoyu oluştur (eğer yoksa)
    try:
        api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True)
        print(f"Hugging Face model deposu hazır: {REPO_ID}")
    except Exception as e:
        print(f"Repo oluşturulurken hata (Token eksik veya yetkisiz olabilir): {e}")
        return

    print("Yenilenen modeller Hugging Face'e yükleniyor...")
    for model_name in models_to_upload():
        model_path = WEIGHTS_DIR / model_name
        if model_path.exists():
            print(f"Yükleniyor: {model_name}...")
            api.upload_file(
                path_or_fileobj=str(model_path),
                path_in_repo=model_name,
                repo_id=REPO_ID,
                repo_type="model"
            )
            print(f"Başarılı: {model_name}")
        else:
            print(f"HATA: {model_name} bulunamadı!")
            
    print(f"Tüm modeller başarıyla https://huggingface.co/{REPO_ID} adresine yüklendi.")

if __name__ == "__main__":
    upload_to_hf()
