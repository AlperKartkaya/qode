import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from datasets import load_dataset
from torch.utils.data import DataLoader, Dataset
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from smart_road_safety.analysis.model_inference import _enhance_crop_for_classification


class HFImageDataset(Dataset):
    def __init__(self, hf_dataset, transform=None):
        self.dataset = hf_dataset
        self.transform = transform
        
        features = self.dataset.features
        self.image_col = next(k for k, v in features.items() if hasattr(v, 'id') or type(v).__name__ == 'Image')
        
        self.label_col = None
        for field in ["label", "etiket", "class", "action"]:
            if field in features:
                self.label_col = field
                break

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

def train_model():
    print("Loading cleaned QoDe-5G/qode-driver-behaviors dataset from Hugging Face...")
    try:
        hf_dataset = load_dataset("QoDe-5G/qode-driver-behaviors", split="train", cache_dir="./hf_temp_cache")
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        return
        
    print(f"Veri seti yüklendi: {len(hf_dataset)} resim.")
    
    features = hf_dataset.features
    label_col = None
    for field in ["label", "etiket", "class", "action"]:
        if field in features:
            label_col = field
            break
            
    classes = features[label_col].names if hasattr(features[label_col], "names") else []
    print(f"Tespit edilen sınıflar: {classes}")

    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.5, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    pytorch_dataset = HFImageDataset(hf_dataset, transform=train_transforms)
    dataloader = DataLoader(pytorch_dataset, batch_size=16, shuffle=True)
    
    model = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.DEFAULT)
    
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(classes))
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    model = model.to(device)
    print(f"Eğitim cihazı: {device}")
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    num_epochs = 5
    print("Eğitim başlıyor...")
    
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
            
        epoch_loss = running_loss / len(pytorch_dataset)
        epoch_acc = corrects.float() / len(pytorch_dataset)
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {epoch_loss:.4f} - Acc: {epoch_acc:.4f}")
        
    out_dir = Path("data/weights")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "driver_classifier.pt"
    
    print("Modeli TorchScript formatına çeviriyoruz (C++ ve inference için gerekli)...")
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save(str(out_path))
    
    print(f"Model başarıyla {out_path} dosyasına kaydedildi!")

if __name__ == "__main__":
    train_model()
