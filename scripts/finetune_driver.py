import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import cv2
import os
import sys
from pathlib import Path

# Prevent OpenCV memory leaks
cv2.setNumThreads(0)

class FineTuneDataset(Dataset):
    def __init__(self, images_dir, labels_dir, transform=None):
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.transform = transform
        
        self.samples = []
        self.classes = ['arkaya_bakma', 'emniyet_kemeri_ihlali', 'esneme', 
                       'etrafa_bakinma', 'guvenli_surus', 'sigara_icme', 
                       'su_icme', 'telefonla_konusma', 'uyuklama']
                       
        for label_file in os.listdir(labels_dir):
            if label_file.endswith('.txt'):
                frame_name = label_file.replace('.txt', '.jpg')
                img_path = os.path.join(images_dir, frame_name)
                
                if os.path.exists(img_path):
                    with open(os.path.join(labels_dir, label_file), 'r') as f:
                        for line in f:
                            cat, label = line.strip().split(',')
                            if cat == 'sofor_eylemi' and label in self.classes:
                                self.samples.append((img_path, self.classes.index(label)))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label

def finetune():
    print("Initializing model...")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    
    # 1. Load base architecture
    model = models.efficientnet_b2()
    num_ftrs = model.classifier[1].in_features
    classes = ['arkaya_bakma', 'emniyet_kemeri_ihlali', 'esneme', 
               'etrafa_bakinma', 'guvenli_surus', 'sigara_icme', 
               'su_icme', 'telefonla_konusma', 'uyuklama']
    model.classifier[1] = nn.Linear(num_ftrs, len(classes))
    
    # 2. Load TorchScript state dict into base architecture
    weights_path = "data/weights/driver_classifier.pt"
    if not os.path.exists(weights_path):
        print(f"Error: Base model {weights_path} not found!")
        sys.exit(1)
        
    print("Loading base weights...")
    traced_model = torch.jit.load(weights_path, map_location="cpu")
    model.load_state_dict(traced_model.state_dict())
    model = model.to(device)
    
    # 3. Prepare Dataset
    train_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    dataset = FineTuneDataset("data/finetune/images", "data/finetune/labels", transform=train_transforms)
    if len(dataset) == 0:
        print("No fine-tuning samples found! Did you run finetune_faz2.py?")
        sys.exit(1)
        
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
    
    # 4. Fine-Tune with LOW learning rate
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0001) # Low LR to prevent Catastrophic Forgetting
    
    num_epochs = 3
    print(f"Starting Fine-Tuning on {len(dataset)} Faz 2 samples...")
    
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
        
    # 5. Save the fine-tuned model
    print("Saving fine-tuned model...")
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    traced_model_new = torch.jit.trace(model, dummy_input)
    traced_model_new.save("data/weights/driver_classifier_finetuned.pt")
    
    print("Fine-tuning complete! Saved to data/weights/driver_classifier_finetuned.pt")

if __name__ == "__main__":
    finetune()
