"""
Quick verification script to display downloaded Sentinel-2 images.
Shows image details and creates a summary visualization.
"""

from PIL import Image
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

def main():
    print("="*70)
    print("SATELLITE IMAGES VERIFICATION")
    print("="*70)

    # Get all downloaded images
    image_dir = Path("satellite_images")
    images = sorted(image_dir.glob("hotspot_*.png"))

    print(f"\nFound {len(images)} images:\n")

    # Display info for each image
    total_size_mb = 0
    for img_path in images:
        img = Image.open(img_path)
        size_mb = img_path.stat().st_size / (1024 * 1024)
        total_size_mb += size_mb

        print(f"✓ {img_path.name}")
        print(f"   Size: {img.size[0]}x{img.size[1]} pixels, {size_mb:.1f} MB")
        print()

    print(f"Total size: {total_size_mb:.1f} MB")

    # Create a summary visualization (grid of thumbnails)
    print("\nCreating summary visualization...")

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle('Sentinel-2 Imagery - Fire Hotspots', fontsize=16)

    for idx, (img_path, ax) in enumerate(zip(images, axes.flat)):
        img = Image.open(img_path)
        ax.imshow(img)
        ax.set_title(f"Hotspot {idx + 1}", fontsize=10)
        ax.axis('off')

    plt.tight_layout()

    output_path = "satellite_images_summary.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Saved summary visualization: {output_path}")

    print("\n" + "="*70)
    print("✓ All images verified successfully!")
    print("="*70)
    print("\nNext steps:")
    print("  - Day 3: Extract thermal bands and compute temperature")
    print("  - Day 4: Train anomaly detection model")
    print("  - Day 5: Create visualization dashboard")

if __name__ == "__main__":
    main()
