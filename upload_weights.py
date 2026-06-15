"""
upload_weights.py — Eğitilmiş model ağırlıklarını Hugging Face Hub'a yükle

Kullanım:
    # Önce login yap (tek seferlik):
    huggingface-cli login
    # veya: export HF_TOKEN="hf_xxxx"

    # Sonra yükle:
    python upload_weights.py

Hedef: https://huggingface.co/QoDe-5G/qode-models
"""

import os
import sys
from pathlib import Path

HF_REPO = "QoDe-5G/qode-models"

# Yüklenecek dosyalar: (local_path, repo_içi_dosya_adı)
WEIGHTS_TO_UPLOAD = [
    ("data/weights/driver_classifier.pt",       "driver_classifier.pt"),
    ("data/weights/vehicle_type_classifier.pt", "vehicle_type_classifier.pt"),
]

MODEL_CARD = """\
---
license: mit
language:
- tr
tags:
- computer-vision
- object-detection
- driver-behavior
- road-safety
- teknofest
- yolo
- efficientnet
---

# QoDe — Smart Road Safety Model Weights

TEKNOFEST 2026 — 5G ve Yapay Zekâ ile Akıllı Yol Güvenliği Yarışması

## Model Dosyaları

| Dosya | Mimari | Görev | Sınıflar |
|---|---|---|---|
| `driver_classifier.pt` | EfficientNet-B2 | Sürücü davranışı sınıflandırma | arkaya_bakma, etrafa_bakinma, su_icme, telefonla_konusma |
| `vehicle_type_classifier.pt` | EfficientNet-B0 | Araç tipi sınıflandırma | sedan, suv, hatchback, pickup, minibus, panelvan, kamyon |

## Kullanım

```python
from huggingface_hub import hf_hub_download
import torch
from torchvision import models
import torch.nn as nn

# Driver classifier
path = hf_hub_download(repo_id="QoDe-5G/qode-models", filename="driver_classifier.pt")
ckpt = torch.load(path, map_location="cpu")
model = models.efficientnet_b2(weights=None)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(ckpt["class_names"]))
model.load_state_dict(ckpt["model_state_dict"])
model.eval()
print("Classes:", ckpt["class_names"])
```

## Veri Seti

State Farm Distracted Driver Detection (~22k görsel) + Windshield Simulator augmentation.

## Kaynak Kod

[github.com/AlperKartkaya/qode](https://github.com/AlperKartkaya/qode)
"""


def upload():
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("Hata: huggingface_hub yüklü değil.")
        print("      pip install huggingface_hub")
        sys.exit(1)

    # .env dosyasından HF_TOKEN okuma (python-dotenv kurmaya gerek kalmadan)
    env_path = Path(".env")
    env_token = None
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("HF_TOKEN="):
                    env_token = line.strip().split("=", 1)[1].strip().strip("'\"")

    token = os.environ.get("HF_TOKEN") or env_token

    if not token:
        print("[!] Hata: HF_TOKEN bulunamadı.")
        print("    Lütfen .env dosyasına HF_TOKEN=hf_xxxxx ekleyin")
        print("    veya terminalde 'export HF_TOKEN=hf_xxxxx' çalıştırın.")
        sys.exit(1)

    api = HfApi(token=token)

    # ── Repo oluştur (zaten varsa geç) ────────────────────────────────────────
    print(f"[HF] Repo kontrol ediliyor: {HF_REPO}")
    try:
        create_repo(
            repo_id=HF_REPO,
            repo_type="model",
            exist_ok=True,
            token=token,
        )
        print(f"[HF] Repo hazır: https://huggingface.co/{HF_REPO}")
    except Exception as e:
        print(f"[HF] Repo oluşturma hatası: {e}")
        sys.exit(1)

    # ── Model Card yükle ───────────────────────────────────────────────────────
    api.upload_file(
        path_or_fileobj=MODEL_CARD.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=HF_REPO,
        repo_type="model",
    )
    print("[HF] Model card (README.md) yüklendi.")

    # ── Ağırlıkları yükle ─────────────────────────────────────────────────────
    uploaded = 0
    for local_path, repo_filename in WEIGHTS_TO_UPLOAD:
        p = Path(local_path)
        if not p.exists():
            size_mb = p.stat().st_size / 1e6 if p.exists() else 0
            print(f"[SKIP] {local_path} bulunamadı — eğitim yapılmamış olabilir.")
            continue

        size_mb = p.stat().st_size / 1e6
        print(f"[↑] {local_path} ({size_mb:.1f} MB) → {repo_filename} yükleniyor...")
        api.upload_file(
            path_or_fileobj=str(p),
            path_in_repo=repo_filename,
            repo_id=HF_REPO,
            repo_type="model",
        )
        print(f"[✓] {repo_filename} yüklendi.")
        uploaded += 1

    print(f"\n[HF] Tamamlandı! {uploaded} dosya yüklendi.")
    print(f"[HF] Repo: https://huggingface.co/{HF_REPO}")


if __name__ == "__main__":
    upload()
