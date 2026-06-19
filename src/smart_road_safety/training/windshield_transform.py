"""
windshield_transform.py — Torchvision-compatible Windshield Augmentation

Wraps the WindshieldSimulator operations as a composable torchvision transform
for use in the training pipeline. Applies reflection, glass tint, glare, and
resolution loss to simulate the view through a windshield from a roadside camera.

Usage in training transforms:
    from smart_road_safety.training.windshield_transform import WindshieldTransform

    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(288, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomApply([WindshieldTransform()], p=0.5),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
"""

import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class WindshieldTransform:
    """Torchvision-compatible transform that simulates viewing through a windshield.

    When applied, it randomly applies a subset of degradation effects:
      1. Glass reflection overlay (diagonal light gradient)
      2. Windshield glass tint (slight green/blue color shift)
      3. Glare and reduced contrast
      4. Resolution loss from distance (downsample + upsample + blur)

    Each effect has independent probability so the augmentation intensity varies
    naturally across training samples, improving generalisation.

    Args:
        reflection_prob: Probability of adding reflection overlay.
        tint_prob: Probability of adding glass tint.
        glare_prob: Probability of reducing contrast/brightness.
        resolution_loss_prob: Probability of simulating distance-based resolution loss.
    """

    def __init__(
        self,
        reflection_prob: float = 0.7,
        tint_prob: float = 0.6,
        glare_prob: float = 0.8,
        resolution_loss_prob: float = 0.5,
    ):
        self.reflection_prob = reflection_prob
        self.tint_prob = tint_prob
        self.glare_prob = glare_prob
        self.resolution_loss_prob = resolution_loss_prob

    def __call__(self, img: Image.Image) -> Image.Image:
        if not isinstance(img, Image.Image):
            raise TypeError(f"Expected PIL Image, got {type(img)}")

        img = img.convert("RGB")

        if random.random() < self.reflection_prob:
            img = self._add_reflection(img)

        if random.random() < self.tint_prob:
            img = self._apply_tint(img)

        if random.random() < self.glare_prob:
            img = self._apply_glare(img)

        if random.random() < self.resolution_loss_prob:
            img = self._simulate_distance(img)

        return img

    @staticmethod
    def _add_reflection(img: Image.Image) -> Image.Image:
        """Add a synthetic reflection overlay simulating sky/road reflections."""
        width, height = img.size
        intensity = random.uniform(0.08, 0.20)

        # Create diagonal gradient simulating glare
        pixels = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                val = int(120 + 100 * ((x / width) + (y / height)) / 2)
                pixels[y, x] = [val, val, val]

        gradient = Image.fromarray(pixels)
        return Image.blend(img, gradient, intensity)

    @staticmethod
    def _apply_tint(img: Image.Image) -> Image.Image:
        """Apply a slight green/blue tint typical of automotive windshield glass."""
        # Randomise tint colour slightly
        tint_r = random.randint(10, 30)
        tint_g = random.randint(30, 50)
        tint_b = random.randint(20, 40)
        tint_layer = Image.new("RGB", img.size, color=(tint_r, tint_g, tint_b))
        return Image.blend(img, tint_layer, random.uniform(0.05, 0.12))

    @staticmethod
    def _apply_glare(img: Image.Image) -> Image.Image:
        """Reduce contrast and brightness to simulate glass-induced haze."""
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.65, 0.90))
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.75, 0.95))
        return img

    @staticmethod
    def _simulate_distance(img: Image.Image) -> Image.Image:
        """Simulate resolution loss from roadside camera distance."""
        w, h = img.size
        scale = random.uniform(0.35, 0.65)
        small = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            resample=Image.Resampling.BILINEAR,
        )
        pixelated = small.resize((w, h), resample=Image.Resampling.BILINEAR)
        pixelated = pixelated.filter(
            ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.0))
        )
        return pixelated

    def __repr__(self) -> str:
        return (
            f"WindshieldTransform("
            f"reflection_prob={self.reflection_prob}, "
            f"tint_prob={self.tint_prob}, "
            f"glare_prob={self.glare_prob}, "
            f"resolution_loss_prob={self.resolution_loss_prob})"
        )
