import os
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from pathlib import Path
from collections import defaultdict

def evaluate_model():
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Evaluating on device: {device}")
    
    data_dir = Path("data/datasets/processed_state_farm")
    val_dir = data_dir / "val"
    weights_path = Path("data/weights/driver_classifier.pt")
    
    if not val_dir.exists():
        print(f"Error: Validation folder not found at {val_dir}.")
        return
        
    if not weights_path.exists():
        print(f"Error: Model weights not found at {weights_path}. Train the model first.")
        return
        
    # Validation transforms (matching training phase)
    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_dataset = datasets.ImageFolder(str(val_dir), val_transform)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=2)
    
    class_names = val_dataset.classes
    num_classes = len(class_names)
    
    print(f"Loading weights from {weights_path}...")
    checkpoint = torch.load(weights_path, map_location=device)
    
    # Recreate the MobileNetV3 architecture and head
    model = models.mobilenet_v3_small()
    num_features = model.classifier[3].in_features
    model.classifier[3] = nn_linear = torch.nn.Linear(num_features, num_classes)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    # Track True Positives, False Positives, False Negatives per class
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    
    total = 0
    correct = 0
    
    print("\nRunning inference on validation set...")
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            for p, l in zip(preds.cpu().numpy(), labels.cpu().numpy()):
                total += 1
                if p == l:
                    correct += 1
                    tp[l] += 1
                else:
                    fp[p] += 1
                    fn[l] += 1
                    
    accuracy = correct / total if total > 0 else 0
    print(f"\n--- EVALUATION METRICS ---")
    print(f"Overall Accuracy: {accuracy:.4f} ({correct}/{total})")
    print("-" * 50)
    print(f"{'Class Name':<20} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 50)
    
    # Calculate Precision, Recall, and F1 per class
    for i, class_name in enumerate(class_names):
        t_pos = tp[i]
        f_pos = fp[i]
        f_neg = fn[i]
        
        precision = t_pos / (t_pos + f_pos) if (t_pos + f_pos) > 0 else 0.0
        recall = t_pos / (t_pos + f_neg) if (t_pos + f_neg) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"{class_name:<20} | {precision:<10.4f} | {recall:<10.4f} | {f1:<10.4f}")
        
    print("-" * 50)

if __name__ == "__main__":
    evaluate_model()
