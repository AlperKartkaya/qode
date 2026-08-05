import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import cv2
import os
import sys
import numpy as np
from ultralytics import YOLO

cv2.setNumThreads(0)

class FineTuneDataset(Dataset):
    def __init__(self, crop_paths, labels, transform=None):
        self.crop_paths = crop_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.crop_paths)

    def __getitem__(self, idx):
        img_path = self.crop_paths[idx]
        label = self.labels[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label

def extract_crops(images_dir, labels_dir, out_driver_dir, out_face_dir):
    print("Loading YOLO for person detection...")
    yolo_model = YOLO("yolo11n.pt") # Fast model for person detection
    
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    os.makedirs(out_driver_dir, exist_ok=True)
    os.makedirs(out_face_dir, exist_ok=True)
    
    driver_samples = [] # (path, label_idx)
    face_samples = []   # (path, label_idx)
    
    driver_classes = ['arkaya_bakma', 'esneme', 'etrafa_bakinma', 'sigara_icme', 'su_icme', 'telefonla_konusma']
    smoker_classes = ['not_smoking', 'smoking']
    
    for label_file in os.listdir(labels_dir):
        if not label_file.endswith('.txt'): continue
        frame_name = label_file.replace('.txt', '.jpg')
        img_path = os.path.join(images_dir, frame_name)
        if not os.path.exists(img_path): continue
        
        frame = cv2.imread(img_path)
        if frame is None: continue
        
        results = yolo_model(frame, classes=[0], verbose=False) # 0 is person
        person_boxes = []
        for box in results[0].boxes.data:
            x1, y1, x2, y2, conf, cls = box
            person_boxes.append([int(x1), int(y1), int(x2), int(y2)])
            
        if not person_boxes: continue
        person_boxes = sorted(person_boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
        x1, y1, x2, y2 = person_boxes[0]
        driver_crop = frame[y1:y2, x1:x2]
        
        driver_out = os.path.join(out_driver_dir, frame_name)
        cv2.imwrite(driver_out, driver_crop)
        
        # Extract face
        h, w = driver_crop.shape[:2]
        gray = cv2.cvtColor(driver_crop, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        if len(faces) > 0:
            faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
            fx, fy, fw, fh = faces[0]
            margin_x = int(fw * 0.2)
            margin_y = int(fh * 0.3)
            fx1 = max(0, fx - margin_x)
            fy1 = max(0, fy - margin_y)
            fx2 = min(w, fx + fw + margin_x)
            fy2 = min(h, fy + fh + int(margin_y * 1.5))
            face_crop = driver_crop[fy1:fy2, fx1:fx2]
        else:
            face_crop = driver_crop[0:int(h * 0.35), :]
            
        face_out = os.path.join(out_face_dir, frame_name)
        cv2.imwrite(face_out, face_crop)
        
        # Read labels
        with open(os.path.join(labels_dir, label_file), 'r') as f:
            for line in f:
                cat, label = line.strip().split(',')
                if cat == 'sofor_eylemi':
                    if label in driver_classes:
                        driver_samples.append((driver_out, driver_classes.index(label)))
                    if label == 'sigara_icme':
                        face_samples.append((face_out, smoker_classes.index('smoking')))
                    elif label in ['su_icme', 'esneme', 'telefonla_konusma']:
                        face_samples.append((face_out, smoker_classes.index('not_smoking')))
                        
    return driver_samples, face_samples

def finetune_model(model, dataloader, num_classes, save_path, device, num_epochs=3):
    if len(dataloader.dataset) == 0:
        print(f"Skipping {save_path}, no training samples.")
        return
        
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    
    print(f"Starting Fine-Tuning for {save_path} with {len(dataloader.dataset)} samples...")
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
            
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {running_loss/len(dataloader.dataset):.4f} - Acc: {corrects.float()/len(dataloader.dataset):.4f}")
        
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save(save_path)
    print(f"Saved {save_path}")

def main():
    print("Extracting intelligent crops (Driver Body and Face) from full 1080p frames...")
    d_samples, f_samples = extract_crops(
        "data/finetune/images", "data/finetune/labels",
        "data/finetune/crops/driver", "data/finetune/crops/face"
    )
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    train_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # 1. Driver Model (EfficientNet-B2)
    print("\n--- Fine-tuning Driver Classifier ---")
    driver_model = models.efficientnet_b2()
    driver_model.classifier[1] = nn.Linear(driver_model.classifier[1].in_features, 6)
    if os.path.exists("data/weights/driver_classifier.pt"):
        traced_d = torch.jit.load("data/weights/driver_classifier.pt", map_location="cpu")
        driver_model.load_state_dict(traced_d.state_dict())
    driver_model = driver_model.to(device)
    
    d_paths, d_labels = zip(*d_samples) if d_samples else ([], [])
    d_loader = DataLoader(FineTuneDataset(d_paths, d_labels, train_transforms), batch_size=4, shuffle=True)
    finetune_model(driver_model, d_loader, 6, "data/weights/driver_classifier_finetuned.pt", device)
    
    # 2. Smoker Model (MobileNetV3-Small)
    print("\n--- Fine-tuning Smoker Classifier ---")
    smoker_model = models.mobilenet_v3_small()
    smoker_model.classifier[3] = nn.Linear(smoker_model.classifier[3].in_features, 2)
    if os.path.exists("data/weights/smoker_classifier.pt"):
        traced_s = torch.jit.load("data/weights/smoker_classifier.pt", map_location="cpu")
        smoker_model.load_state_dict(traced_s.state_dict())
    smoker_model = smoker_model.to(device)
    
    f_paths, f_labels = zip(*f_samples) if f_samples else ([], [])
    f_loader = DataLoader(FineTuneDataset(f_paths, f_labels, train_transforms), batch_size=4, shuffle=True)
    finetune_model(smoker_model, f_loader, 2, "data/weights/smoker_classifier_finetuned.pt", device)

if __name__ == "__main__":
    main()
