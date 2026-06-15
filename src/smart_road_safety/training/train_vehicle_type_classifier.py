"""
train_vehicle_type_classifier.py — FTR Vehicle Type Classifier

Trains an EfficientNet-B0 model to classify vehicle body types into
the 7 FTR-required categories:
    sedan, suv, hatchback, pickup, minibus, panelvan, kamyon

Data sources (use whichever is available):
  1. Stanford Cars Dataset (fine-grained, 196 classes — we map to FTR 7)
  2. Custom collected images organised into FTR label folders
  3. data/datasets/yolo_ftr_dataset/  (YOLO-labelled crops exported as images)

Usage:
    # Prepare a folder at data/datasets/vehicle_types/ with subdirs per class:
    #   data/datasets/vehicle_types/train/sedan/  ← images
    #   data/datasets/vehicle_types/val/sedan/
    #   ... etc.
    python -m smart_road_safety.training.train_vehicle_type_classifier
"""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms, models
from pathlib import Path
from collections import Counter

# ── FTR vehicle type labels ───────────────────────────────────────────────────
FTR_VEHICLE_TYPES = [
    "hatchback",
    "kamyon",
    "minibus",
    "panelvan",
    "pickup",
    "sedan",
    "suv",
]

# ── Stanford Cars → FTR mapping (coarse, not exhaustive) ─────────────────────
# Extend this dict if using Stanford Cars; the key is the Stanford class name
# (or a substring). Only used if dataset_mapper integration is added later.
STANFORD_TO_FTR: dict[str, str] = {
    "sedan":     "sedan",
    "coupe":     "sedan",
    "convertible": "sedan",
    "hatchback": "hatchback",
    "wagon":     "hatchback",
    "suv":       "suv",
    "van":       "minibus",
    "minivan":   "minibus",
    "pickup":    "pickup",
    "truck":     "kamyon",
    "cab":       "pickup",
}


def make_weighted_sampler(dataset: datasets.ImageFolder) -> WeightedRandomSampler:
    class_counts = Counter(dataset.targets)
    total = sum(class_counts.values())
    w = {cls: total / cnt for cls, cnt in class_counts.items()}
    sample_weights = [w[t] for t in dataset.targets]
    return WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)


def train_model(
    data_dir: str = "data/datasets/qode-vehicle-types",
    epochs: int = 20,
    batch_size: int = 32,
    lr: float = 3e-4,
    freeze_epochs: int = 5,
) -> None:
    data_path  = Path(data_dir)
    train_dir  = data_path / "train"
    val_dir    = data_path / "val"

    if not train_dir.exists():
        print(
            f"[VehicleTrain] ERROR: Dataset not found at {train_dir}\n"
            "               Prepare vehicle image folders first.\n"
            "               Expected: data/datasets/vehicle_types/train/<class>/\n"
            "               Classes:  " + ", ".join(FTR_VEHICLE_TYPES)
        )
        return

    # ── Device ────────────────────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[VehicleTrain] Device: {device}")

    # ── Transforms ────────────────────────────────────────────────────────────
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.75, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
        transforms.RandomRotation(8),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_ds = datasets.ImageFolder(str(train_dir), train_tf)
    val_ds   = datasets.ImageFolder(str(val_dir),   val_tf)

    sampler = make_weighted_sampler(train_ds)
    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler,    num_workers=4)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False,      num_workers=4)

    class_names = train_ds.classes
    num_classes = len(class_names)
    print(f"[VehicleTrain] Classes ({num_classes}): {class_names}")
    print(f"[VehicleTrain] Train: {len(train_ds)}  Val: {len(val_ds)}")

    # ── Model: EfficientNet-B0 (lighter than B2, good for 7-class problem) ────
    print("[VehicleTrain] Loading EfficientNet-B0 (ImageNet pretrained)…")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model = model.to(device)

    # Freeze backbone for warm-up
    for param in model.features.parameters():
        param.requires_grad = False

    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    criterion = nn.CrossEntropyLoss()

    weights_dir = Path("data/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)
    best_path = weights_dir / "vehicle_type_classifier.pt"
    best_acc  = 0.0

    print("\n[VehicleTrain] ── Training ──")
    for epoch in range(epochs):
        if epoch == freeze_epochs:
            print(f"[VehicleTrain] Epoch {epoch+1}: Unfreezing all layers.")
            for param in model.features.parameters():
                param.requires_grad = True
            optimizer = optim.AdamW([
                {"params": model.features.parameters(), "lr": lr * 0.1},
                {"params": model.classifier.parameters(), "lr": lr},
            ], weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=epochs - freeze_epochs, eta_min=1e-6
            )

        print(f"\n  Epoch {epoch+1}/{epochs}")
        for phase, loader, ds in [("train", train_loader, train_ds), ("val", val_loader, val_ds)]:
            model.train() if phase == "train" else model.eval()
            loss_sum, correct = 0.0, 0
            for inputs, labels in loader:
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == "train"):
                    out = model(inputs)
                    loss = criterion(out, labels)
                    if phase == "train":
                        loss.backward(); optimizer.step()
                loss_sum += loss.item() * inputs.size(0)
                correct  += (out.argmax(1) == labels).sum().item()
            acc = correct / len(ds)
            print(f"    {phase:5s}  Loss: {loss_sum/len(ds):.4f}  Acc: {acc:.4f}")
            if phase == "val" and acc > best_acc:
                best_acc = acc
                torch.save({
                    "model_state_dict":   model.state_dict(),
                    "class_names":        class_names,
                    "model_architecture": "efficientnet_b0",
                    "val_accuracy":       best_acc,
                    "epoch":              epoch + 1,
                }, best_path)
                print(f"    ✓ Saved → {best_path}  (Acc={best_acc:.4f})")
        scheduler.step()

    print(f"\n[VehicleTrain] Done.  Best Val Acc: {best_acc:.4f}")
    print(f"[VehicleTrain] Weights: {best_path.resolve()}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Train EfficientNet-B0 vehicle type classifier")
    p.add_argument("--data-dir",      default="data/datasets/vehicle_types")
    p.add_argument("--epochs",        type=int,   default=20)
    p.add_argument("--batch-size",    type=int,   default=32)
    p.add_argument("--lr",            type=float, default=3e-4)
    p.add_argument("--freeze-epochs", type=int,   default=5)
    args = p.parse_args()
    train_model(
        data_dir=args.data_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        freeze_epochs=args.freeze_epochs,
    )
