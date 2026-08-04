import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from datasets import load_dataset, Features, Image as HFImage, ClassLabel
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import cv2
import numpy as np

# Prevent OpenCV from spawning extra threads that cause RAM OOM on small VMs
cv2.setNumThreads(0)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from smart_road_safety.analysis.model_inference import _enhance_crop_for_classification


class HFImageDataset(Dataset):
    def __init__(self, hf_dataset, transform=None):
        self.dataset = hf_dataset
        self.transform = transform
        
        # Find image and label columns
        features = self.dataset.features
        self.image_col = next(k for k, v in features.items() if hasattr(v, 'id') or type(v).__name__ == 'Image')
        
        self.label_col = None
        for field in ["label", "etiket", "class", "action"]:
            if field in features:
                self.label_col = field
                break
        
        if self.label_col is None:
            # Fallback to the first column that isn't the image
            for k in features.keys():
                if k != self.image_col:
                    self.label_col = k
                    break
            
        if self.label_col is None:
            print(f"Uyarı: Etiket (label) kolonu bulunamadı. Mevcut kolonlar: {list(features.keys())}")

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        item = self.dataset[idx]
        img = item[self.image_col]
        label = item[self.label_col]
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Exact match with inference preprocessing (requires BGR for OpenCV)
        img_np = np.array(img)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        img_enhanced_bgr = _enhance_crop_for_classification(img_bgr)
        img_enhanced_rgb = cv2.cvtColor(img_enhanced_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img_enhanced_rgb)
            
        if self.transform:
            img = self.transform(img)
            
        return img, label

def train_smoker_model():
    print("Loading smoker-detection dataset from Hugging Face...")
    try:
        schema = Features({
            "image": HFImage(),
            "label": ClassLabel(names=["not_smoking", "smoking"])
        })
        dataset = load_dataset("QoDe-5G/qode-smoker-detection", split="train", cache_dir="./hf_temp_cache", features=schema)
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        sys.exit(1)
        
    print(f"Loaded {len(dataset)} images.")
    
    # We need to map labels. The default imagefolder creates an integer label.
    features = dataset.features
    label_col = None
    for field in ["label", "etiket", "class", "action"]:
        if field in features:
            label_col = field
            break
            
    if label_col is None:
        for k in features.keys():
            if type(features[k]).__name__ != 'Image' and not hasattr(features[k], 'id'):
                label_col = k
                break
                
    if label_col is None:
        print(f"HATA: Veri setinde etiket kolonu bulunamadı! Kolonlar: {list(features.keys())}")
        print("ÇÖZÜM: Veri setiniz HuggingFace'te oluşturulurken etiketsiz (labelsiz) yüklenmiş.")
        sys.exit(1)
        
    classes = features[label_col].names if hasattr(features[label_col], "names") else ["not_smoking", "smoking"]
    print(f"Detected classes: {classes}")

    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)), 
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    pytorch_dataset = HFImageDataset(dataset, transform=train_transforms)
    dataloader = DataLoader(pytorch_dataset, batch_size=8, shuffle=True)
    
    # We use a lightweight MobileNetV3 for fast face classification
    print("Initializing MobileNetV3 model...")
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    
    num_ftrs = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_ftrs, len(classes))
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    model = model.to(device)
    print(f"Training on device: {device}")
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    num_epochs = 5
    print("Starting training...")
    
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        corrects = 0
        
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            _, preds = torch.max(outputs, 1)
            running_loss += loss.item() * inputs.size(0)
            corrects += torch.sum(preds == labels.data)
            
        epoch_loss = running_loss / len(dataset)
        epoch_acc = corrects.float() / len(dataset)
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {epoch_loss:.4f} - Acc: {epoch_acc:.4f}")
        
    out_dir = "data/weights"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "smoker_classifier.pt")
    
    # Save using torch.jit.script for C++ inference compatibility, as expected by model_inference.py
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save(out_path)
    
    print(f"Model successfully saved to {out_path}!")

if __name__ == "__main__":
    train_smoker_model()
