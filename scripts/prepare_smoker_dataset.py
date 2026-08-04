import os
import glob
from PIL import Image as PILImage
from datasets import load_dataset, Dataset, Features, Image, ClassLabel, concatenate_datasets
from huggingface_hub import login

def prepare_smoker_dataset():
    # Login
    token_path = os.path.expanduser("~/.cache/huggingface/token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        login(token=token)
    else:
        print("HF token not found!")
        return

    repo_id_new = "QoDe-5G/qode-smoker-detection"
    local_dir = os.path.expanduser("~/qode/data/datasets/smoker-detection")

    print("1. Yerel (Local) smoker-detection resimlerini toplayıp etiketliyoruz...")
    local_images = []
    local_labels = []

    # Walk through the local directory manually to avoid 'imagefolder' bugs
    if os.path.exists(local_dir):
        valid_exts = {".jpg", ".jpeg", ".png"}
        for root, _, files in os.walk(local_dir):
            for file in files:
                if os.path.splitext(file)[1].lower() in valid_exts:
                    full_path = os.path.join(root, file)
                    # Check folder name or file name for labels
                    lower_path = full_path.lower()
                    if "not_smoking" in lower_path or "non_smoking" in lower_path or "non-smoking" in lower_path:
                        label = 0 # not_smoking
                    elif "smoking" in lower_path:
                        label = 1 # smoking
                    else:
                        continue # Skip unknown
                    
                    try:
                        # Verify it's a valid image
                        with PILImage.open(full_path) as img:
                            img.verify()
                        local_images.append(full_path)
                        local_labels.append(label)
                    except Exception:
                        pass
    
    print(f"Yerel klasörden toplam {len(local_images)} geçerli resim bulundu.")
    
    # Create HF dataset from local lists
    local_ds = Dataset.from_dict({
        "image": local_images,
        "label": local_labels
    }).cast_column("image", Image())

    print("\n2. QoDe-5G/qode-training-data veri setinden 'sigara_icme' (araba camı çekimleri) alınıyor...")
    remote_images = []
    remote_labels = []
    
    try:
        training_data = load_dataset("QoDe-5G/qode-training-data", split="train")
        features = training_data.features
        
        label_field = None
        for field in ["label", "etiket", "class", "action", "sofor_eylemi"]:
            if field in features:
                label_field = field
                break
                
        smoking_id = -1
        normal_id = -1
        
        if label_field and hasattr(features[label_field], "names"):
            for i, name in enumerate(features[label_field].names):
                if "sigara" in name.lower() or "smoking" in name.lower():
                    smoking_id = i
                elif "normal" in name.lower():
                    normal_id = i
                    
        if smoking_id != -1 and normal_id != -1:
            print(f"Remote'da sigara ID: {smoking_id}, Normal Sürüş ID: {normal_id}")
            for item in training_data:
                if item[label_field] == smoking_id:
                    remote_images.append(item["image"])
                    remote_labels.append(1) # smoking
                elif item[label_field] == normal_id:
                    # Sadece 1500 tane normal sürüş alalım ki denge bozulmasın
                    if remote_labels.count(0) < 1500:
                        remote_images.append(item["image"])
                        remote_labels.append(0) # not_smoking
        
        print(f"Remote veri setinden {len(remote_images)} adet araç-içi zorlu resim başarıyla çekildi.")
    except Exception as e:
        print(f"Uyarı: qode-training-data okunamadı: {e}")
        
    # Remote dataset
    if len(remote_images) > 0:
        remote_ds = Dataset.from_dict({
            "image": remote_images,
            "label": remote_labels
        })
        
        print("\n3. Yerel ve Remote veri setleri birleştiriliyor (Merge)...")
        final_dataset = concatenate_datasets([local_ds, remote_ds])
    else:
        final_dataset = local_ds
        
    # Define exact ClassLabel features so the training scripts can read it!
    features = Features({
        "image": Image(),
        "label": ClassLabel(names=["not_smoking", "smoking"])
    })
    
    final_dataset = final_dataset.cast(features)
    
    # Shuffle
    final_dataset = final_dataset.shuffle(seed=42)
    
    print(f"\n4. Oluşturulan KUSURSUZ Final Veri Seti: {len(final_dataset)} resim.")
    print("HuggingFace'e yükleniyor (Pushing to Hub)... Lütfen bekleyin, biraz sürebilir.")
    
    final_dataset.push_to_hub(repo_id_new)
    print("\n✅ Harika! Veri seti tüm etiketleriyle (labels) birlikte başarıyla HuggingFace'e yüklendi!")

if __name__ == "__main__":
    prepare_smoker_dataset()
