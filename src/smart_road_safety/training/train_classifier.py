"""
train_classifier.py — Driver Behaviour Classifier Training

Model: EfficientNet-B2 (torchvision pretrained on ImageNet)
Data:  data/datasets/qode-driver-behaviors/  (train/ val/ subfolders)
       Run build_datasets.py first to prepare the dataset.

Features:
  • Progressive layer unfreezing (feature extractor frozen for first N epochs)
  • CosineAnnealingLR scheduler for stable convergence
  • WeightedRandomSampler to handle class imbalance
  • WindshieldTransform augmentation for outer-camera domain adaptation
  • Saves best validation-accuracy checkpoint to data/weights/driver_classifier.pt
"""

import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms, models
from pathlib import Path
from collections import Counter
from tqdm import tqdm

from smart_road_safety.training.windshield_transform import WindshieldTransform


def make_weighted_sampler(dataset: datasets.ImageFolder) -> WeightedRandomSampler:
    """Build a sampler that oversamples minority classes to counteract imbalance."""
    class_counts = Counter(dataset.targets)
    total = sum(class_counts.values())
    class_weight = {cls_idx: total / count for cls_idx, count in class_counts.items()}
    sample_weights = [class_weight[label] for label in dataset.targets]
    return WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )


def train_model(
    epochs: int = 20,
    batch_size: int = 32,
    lr: float = 3e-4,
    freeze_epochs: int = 5,
):
    """
    Args:
        epochs: Total training epochs.
        batch_size: Mini-batch size.
        lr: Initial learning rate for the classifier head.
        freeze_epochs: Number of epochs to keep the feature extractor frozen
                       before progressive unfreezing.
    """
    # ── Device ────────────────────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[Train] Device: {device}")

    # ── Dataset paths ─────────────────────────────────────────────────────────
    data_dir  = Path("data/datasets/qode-driver-behaviors")
    train_dir = data_dir / "train"
    val_dir   = data_dir / "val"

    if not train_dir.exists() or not val_dir.exists():
        print(
            f"[Train] ERROR: Processed dataset not found at {data_dir}.\n"
            "        Run:  python src/smart_road_safety/training/build_datasets.py"
        )
        return

    # ── Transforms ─────────────────────────────────────────────────────────────
    # WindshieldTransform simulates the outer-camera-through-glass view.
    # Applied with 50% probability to teach the model to handle both clear
    # (inner-camera) and degraded (outer-camera) inputs.
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(288, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
        transforms.RandomRotation(10),
        transforms.RandomApply([WindshieldTransform()], p=0.5),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize(320),
        transforms.CenterCrop(288),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # ── DataLoaders ───────────────────────────────────────────────────────────
    train_ds = datasets.ImageFolder(str(train_dir), train_tf)
    val_ds   = datasets.ImageFolder(str(val_dir),   val_tf)

    sampler = make_weighted_sampler(train_ds)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        sampler=sampler,        # weighted — replaces shuffle=True
        num_workers=4,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=device.type == "cuda",
    )

    class_names = train_ds.classes
    num_classes = len(class_names)
    print(f"[Train] Classes ({num_classes}): {class_names}")
    print(f"[Train] Train samples: {len(train_ds)}  Val samples: {len(val_ds)}")

    # ── Model: EfficientNet-B2 ────────────────────────────────────────────────
    print("[Train] Loading EfficientNet-B2 (ImageNet pretrained)…")
    model = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.DEFAULT)

    # Replace classifier head for our number of classes
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model = model.to(device)

    # ── Freeze feature extractor for warm-up phase ───────────────────────────
    for param in model.features.parameters():
        param.requires_grad = False
    print(f"[Train] Feature extractor frozen for first {freeze_epochs} epoch(s).")

    # Only optimise the classifier head initially
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr, weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    criterion = nn.CrossEntropyLoss()

    weights_dir = Path("data/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)
    best_model_path = weights_dir / "driver_classifier.pt"
    best_acc = 0.0

    # ── Training loop ─────────────────────────────────────────────────────────
    print("\n[Train] ── Starting Training ──")
    for epoch in range(epochs):
        # Progressive unfreezing: unfreeze all layers after freeze_epochs
        if epoch == freeze_epochs:
            print(f"[Train] Epoch {epoch+1}: Unfreezing full feature extractor.")
            for param in model.features.parameters():
                param.requires_grad = True
            # Re-create optimizer with full param set + lower LR for feature layers
            optimizer = optim.AdamW([
                {"params": model.features.parameters(), "lr": lr * 0.1},
                {"params": model.classifier.parameters(), "lr": lr},
            ], weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=epochs - freeze_epochs, eta_min=1e-6
            )

        print(f"\n[Train] Epoch {epoch+1}/{epochs}  LR={scheduler.get_last_lr()}")
        print("-" * 40)

        for phase, loader, dataset in [
            ("train", train_loader, train_ds),
            ("val",   val_loader,   val_ds),
        ]:
            model.train() if phase == "train" else model.eval()
            running_loss = 0.0
            running_correct = 0

            for inputs, labels in tqdm(loader, desc=f"  {phase.capitalize():5s}", leave=False):
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == "train"):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)
                    if phase == "train":
                        loss.backward()
                        optimizer.step()

                running_loss    += loss.item() * inputs.size(0)
                running_correct += torch.sum(preds == labels).item()

            epoch_loss = running_loss / len(dataset)
            epoch_acc  = running_correct / len(dataset)
            print(f"  {phase.capitalize():5s}  Loss: {epoch_loss:.4f}  Acc: {epoch_acc:.4f}")

            if phase == "val" and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save({
                    "model_state_dict":   model.state_dict(),
                    "class_names":        class_names,
                    "model_architecture": "efficientnet_b2",
                    "val_accuracy":       best_acc,
                    "epoch":              epoch + 1,
                }, best_model_path)
                print(f"  ✓ New best model saved → {best_model_path}  (Acc={best_acc:.4f})")

        scheduler.step()

    print(f"\n[Train] ── Complete ──  Best Val Acc: {best_acc:.4f}")
    print(f"[Train] Weights: {best_model_path.resolve()}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Train EfficientNet-B2 driver behaviour classifier")
    p.add_argument("--epochs",        type=int,   default=20,  help="Total training epochs")
    p.add_argument("--batch-size",    type=int,   default=32,  help="Mini-batch size")
    p.add_argument("--lr",            type=float, default=3e-4, help="Initial learning rate")
    p.add_argument("--freeze-epochs", type=int,   default=5,   help="Epochs to keep backbone frozen")
    args = p.parse_args()

    train_model(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        freeze_epochs=args.freeze_epochs,
    )
