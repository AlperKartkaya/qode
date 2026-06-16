import os
from pathlib import Path
from huggingface_hub import HfApi

# Hugging Face Repository adı (kendi kullanıcı adınıza göre değiştirin, örn: QoDe-5G/qode-training-data)
REPO_ID = "QoDe-5G/qode-training-data" 
DATA_DIR = Path("data/training_data")

def upload_to_hf():
    if not DATA_DIR.exists():
        print(f"Hata: {DATA_DIR} bulunamadı.")
        return
        
    api = HfApi()
    
    # Repoyu oluştur (eğer yoksa)
    try:
        api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)
        print(f"Hugging Face veri seti deposu hazır: {REPO_ID}")
    except Exception as e:
        print(f"Repo oluşturulurken hata (Token eksik olabilir): {e}")
        print("Lütfen terminalde 'huggingface-cli login' yaptığınızdan emin olun.")
        return

    print("Veriler yükleniyor... Bu işlem veri boyutuna göre biraz sürebilir.")
    api.upload_folder(
        folder_path=str(DATA_DIR),
        repo_id=REPO_ID,
        repo_type="dataset",
        path_in_repo="." # Reponun kök dizinine yükle
    )
    print(f"Başarılı! Veriler başarıyla {REPO_ID} adresine yüklendi.")

if __name__ == "__main__":
    upload_to_hf()
