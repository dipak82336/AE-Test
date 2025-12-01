import os
from PIL import Image

image_dir = r"e:\Python\Data\images"
files = ["TechBG.png", "Nature.png", "City.png", "Logo.png"]

print(f"Checking images in {image_dir}...")

for filename in files:
    path = os.path.join(image_dir, filename)
    if os.path.exists(path):
        try:
            print(f"Processing {filename}...")
            # Open the image
            with Image.open(path) as img:
                # Force convert to RGBA to ensure consistency
                img = img.convert("RGBA")
                # Save it back as PNG, overwriting the original
                img.save(path, "PNG")
            print(f"Successfully fixed {filename}")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
    else:
        print(f"File not found: {filename}")
