import os
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_turkish_plate_text() -> str:
    # Format: City Code (01-81) + 1-3 letters + 2-4 digits
    city = f"{random.randint(1, 81):02d}"
    letters_len = random.choice([1, 2, 3])
    # Avoid Turkish characters, plus 'I' and 'O' to prevent OCR confusion
    letters = "".join(random.choices(string.ascii_uppercase.replace("I", "").replace("O", ""), k=letters_len))
    digits_len = 5 - letters_len if random.random() > 0.5 else 6 - letters_len
    digits_len = max(2, min(digits_len, 4))
    digits = "".join(random.choices(string.digits, k=digits_len))
    return f"{city}{letters}{digits}"

def get_macos_font_path() -> str:
    paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return ""

def draw_plate(text: str, font_path: str, output_dir: str, file_name: str) -> None:
    # Standard Turkish plate ratio: 520x110 mm (~ 520x110 pixels)
    img = Image.new("RGB", (520, 110), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw blue EU band on the left (approx 40px wide)
    draw.rectangle([0, 0, 40, 110], fill=(0, 51, 153))
    
    # Draw TR text inside blue band
    if font_path:
        try:
            band_font = ImageFont.truetype(font_path, 18)
            draw.text((8, 75), "TR", font=band_font, fill="white")
        except Exception:
            pass
            
    # Draw black border
    draw.rectangle([3, 3, 517, 107], outline="black", width=4)
    
    # Draw the license plate text
    if font_path:
        try:
            font = ImageFont.truetype(font_path, 72)
            # Calculate text size and center it
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((520 - w) / 2 + 15, (110 - h) / 2 - 5), text, font=font, fill="black")
        except Exception:
            draw.text((60, 20), text, fill="black")
    else:
        # Fallback if no font file is found
        draw.text((60, 40), text, fill="black")
        
    # Apply synthetic noise (blur, slight rotation, perspective, illumination)
    # 1. Blur
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.1, 1.0)))
    
    # 2. Lighting / Color Jitter
    if random.random() > 0.5:
        # Add a slight shadow or gradient overlay
        shadow = Image.new("L", img.size, color=255)
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([0, 0, random.randint(100, 400), 110], fill=random.randint(200, 240))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=30))
        img = Image.composite(img, Image.new("RGB", img.size, "black"), shadow)

    # Save image
    os.makedirs(output_dir, exist_ok=True)
    img.save(os.path.join(output_dir, file_name))

def main():
    output_dir = "data/datasets/synthetic_plates"
    labels_file = os.path.join(output_dir, "train_list.txt")
    font_path = get_macos_font_path()
    
    if not font_path:
        print("Warning: No system TrueType font found. Output text will use default PIL font.")
        
    print(f"Generating 100 synthetic plates to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(labels_file, "w", encoding="utf-8") as lf:
        for i in range(100):
            plate_text = generate_turkish_plate_text()
            file_name = f"plate_{i:04d}.png"
            draw_plate(plate_text, font_path, output_dir, file_name)
            # PaddleOCR label format: file_name \t plate_text
            lf.write(f"{file_name}\t{plate_text}\n")
            
    print(f"Generation complete. Labels saved in {labels_file}")

if __name__ == "__main__":
    main()
