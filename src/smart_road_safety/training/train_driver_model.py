import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader
from pathlib import Path

# Veri seti yolu
DATA_DIR = Path("data/datasets/qode-driver-behaviors/train")

# Veri artırma (Data Augmentation) adımları
# Kullanıcının endişesi: "Biz uzaktan çekiyoruz, fotoğraflar küçük olabilir"
# Çözüm: RandomResizedCrop ve ColorJitter ekleyerek modeli düşük çözünürlük ve uzak çekimlere hazırlıyoruz.
train_transforms = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.5, 1.0)), # %50'ye kadar küçülmüş (uzak) yüzleri simüle eder
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2), # Farklı ışık koşulları
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def train_model():
    if not DATA_DIR.exists():
        print(f"Hata: {DATA_DIR} bulunamadı. Lütfen önce veri çıkarma scriptlerini çalıştırın.")
        return
        
    print("Veri seti yükleniyor...")
    dataset = datasets.ImageFolder(DATA_DIR, transform=train_transforms)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    
    classes = dataset.classes
    print(f"Tespit edilen sınıflar: {classes}")
    
    # Önceden eğitilmiş EfficientNet-B2 modelini yüklüyoruz
    model = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.DEFAULT)
    
    # Son katmanı kendi sınıf sayımıza göre (esneme, sigara_icme vb.) değiştiriyoruz
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
            
        epoch_loss = running_loss / len(dataset)
        epoch_acc = corrects.float() / len(dataset)
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {epoch_loss:.4f} - Acc: {epoch_acc:.4f}")
        
    # Sınıf eşleşmelerini (Class mapping) kaydetmemiz lazım ki inference yaparken bilelim
    model.class_to_idx = dataset.class_to_idx
    
    out_path = Path("driver_classifier_custom.pt")
    torch.save(model, out_path)
    print(f"Model başarıyla {out_path} dosyasına kaydedildi!")

if __name__ == "__main__":
    train_model()
