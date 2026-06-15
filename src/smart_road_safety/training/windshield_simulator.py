import os
import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

class WindshieldSimulator:
    """
    Simulates the visual conditions of viewing a driver/passenger from a roadside safety camera
    through a vehicle's front windshield (reflection, tint, glare, blur, and resolution loss).
    """
    
    @staticmethod
    def add_reflection(img: Image.Image, reflection_intensity: float = 0.15) -> Image.Image:
        # Create a synthetic reflection overlay (e.g., sky/clouds gradient or tree silhouette)
        width, height = img.size
        reflection = Image.new("RGB", (width, height), color=(255, 255, 255))
        
        # Draw a simple diagonal gradient to simulate glare/sky reflection
        pixels = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                # Diagonal light pattern
                val = int(120 + 100 * ((x / width) + (y / height)) / 2)
                pixels[y, x] = [val, val, val]
                
        gradient_img = Image.fromarray(pixels)
        # Blend the reflection with the original image
        return Image.blend(img, gradient_img, reflection_intensity)

    @staticmethod
    def apply_glass_tint(img: Image.Image, tint_color: tuple = (20, 40, 30)) -> Image.Image:
        # Most windshields have a slight green or blue tint
        tint_layer = Image.new("RGB", img.size, color=tint_color)
        return Image.blend(img, tint_layer, 0.08)

    @staticmethod
    def apply_glare_and_contrast(img: Image.Image) -> Image.Image:
        # Windshields reduce contrast due to atmospheric haze and glass reflections
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.7, 0.9))
        
        # Slightly reduce brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.8, 0.95))
        return img

    @staticmethod
    def simulate_roadside_camera_quality(img: Image.Image) -> Image.Image:
        # Roadside cameras are far away; driver region has resolution loss
        w, h = img.size
        # Downsample and upsample to simulate pixelation
        scale = random.uniform(0.4, 0.7)
        small_img = img.resize((int(w * scale), int(h * scale)), resample=Image.Resampling.BILINEAR)
        pixelated = small_img.resize((w, h), resample=Image.Resampling.BILINEAR)
        
        # Apply slight motion blur or gaussian blur
        pixelated = pixelated.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.2)))
        return pixelated

    @classmethod
    def transform_image(cls, image_path: str, output_path: str) -> None:
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                
                # Apply pipeline
                img = cls.add_reflection(img, reflection_intensity=random.uniform(0.1, 0.22))
                img = cls.apply_glass_tint(img)
                img = cls.apply_glare_and_contrast(img)
                img = cls.simulate_roadside_camera_quality(img)
                
                # Save result
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                img.save(output_path)
        except Exception as e:
            print(f"Error transforming image {image_path}: {e}")

if __name__ == "__main__":
    # Test simulator on a placeholder if available
    print("Windshield Simulator class loaded successfully.")
