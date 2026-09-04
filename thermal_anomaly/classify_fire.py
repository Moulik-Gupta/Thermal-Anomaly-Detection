"""
Day 3 - Fire Detection Classifier
Uses a pre-trained ViT model (EdBianchi/vit-fire-detection) from Hugging Face
to classify satellite image patches as Fire or No Fire.
Fallback: brightness temperature threshold if model fails.
"""

import os
import sys
import pandas as pd
from PIL import Image
from transformers import pipeline
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving figures


# ─── Configuration ────────────────────────────────────────────────────
CANDIDATES_CSV = "candidates.csv"
IMAGE_DIR = "satellite_images"
OUTPUT_CSV = "classification_results.csv"
SUMMARY_FILE = "classification_summary.txt"
REPORT_IMAGE = "classification_report.png"

# Brightness temperature threshold (Kelvin) for fallback method
BRIGHTNESS_THRESHOLD = 350.0

# Confidence threshold - below this we mark as "Uncertain"
CONFIDENCE_THRESHOLD = 0.60


# ─── Load Model ───────────────────────────────────────────────────────
def load_model():
    """Load the pre-trained fire detection model from Hugging Face."""
    print("Loading fire detection model...")
    try:
        classifier = pipeline(
            "image-classification",
            model="EdBianchi/vit-fire-detection"
        )
        print("Model loaded successfully!\n")
        return classifier
    except Exception as e:
        print(f"WARNING: Could not load model: {e}")
        print("Will use fallback (brightness temperature) method.\n")
        return None


# ─── Build Image Mapping ──────────────────────────────────────────────
def build_image_map(image_dir):
    """
    Build a dictionary mapping hotspot index to image file path.
    Images are named like: hotspot_1_2026-08-23.png
    """
    image_map = {}
    if not os.path.exists(image_dir):
        print(f"ERROR: Image directory '{image_dir}' not found!")
        return image_map

    for filename in os.listdir(image_dir):
        if filename.startswith("hotspot_") and filename.endswith(".png"):
            # Extract index from filename: hotspot_1_2026-08-23.png -> 1
            parts = filename.replace("hotspot_", "").split("_")
            try:
                idx = int(parts[0])
                image_map[idx] = os.path.join(image_dir, filename)
            except ValueError:
                continue

    return image_map


# ─── Classify Single Image ────────────────────────────────────────────
def classify_image(classifier, image_path):
    """
    Run the fire detection model on a single image.
    Returns: (label, confidence)
    """
    try:
        img = Image.open(image_path).convert("RGB")
        results = classifier(img)

        # Results format: [{'label': 'fire', 'score': 0.95}, {'label': 'no_fire', 'score': 0.05}]
        top_result = results[0]
        label = top_result["label"]
        confidence = top_result["score"]

        # Normalize label
        if "fire" in label.lower() and "no" not in label.lower():
            classification = "Fire"
        else:
            classification = "No Fire"

        return classification, confidence

    except Exception as e:
        print(f"  Model error: {e}")
        return None, None


# ─── Fallback: Brightness Threshold ──────────────────────────────────
def classify_by_brightness(bright_ti4):
    """Fallback classification using FIRMS brightness temperature."""
    if bright_ti4 >= BRIGHTNESS_THRESHOLD:
        confidence = min((bright_ti4 - 300) / 100, 1.0)  # Simple scaling
        return "Fire", round(confidence, 4)
    else:
        confidence = min((BRIGHTNESS_THRESHOLD - bright_ti4) / 100, 1.0)
        return "No Fire", round(confidence, 4)


# ─── Main Classification Pipeline ────────────────────────────────────
def main():
    print("=" * 60)
    print("   FIRE DETECTION CLASSIFIER - Day 3")
    print("   Model: EdBianchi/vit-fire-detection (ViT)")
    print("=" * 60)
    print()

    # Load data
    if not os.path.exists(CANDIDATES_CSV):
        print(f"ERROR: '{CANDIDATES_CSV}' not found!")
        sys.exit(1)

    df = pd.read_csv(CANDIDATES_CSV)
    print(f"Loaded {len(df)} hotspot candidates.\n")

    # Load model
    classifier = load_model()

    # Build image map
    image_map = build_image_map(IMAGE_DIR)
    print(f"Found {len(image_map)} satellite images.\n")

    # ─── Run Classification ───────────────────────────────────────
    results = []

    for idx, row in df.iterrows():
        hotspot_idx = idx + 1  # Images are 1-indexed
        lat = row["latitude"]
        lon = row["longitude"]
        bright = row["bright_ti4"]
        date = row["acq_date"]
        frp = row["frp"]

        print(f"Hotspot {hotspot_idx}: ({lat:.4f}, {lon:.4f}) | "
              f"Bright: {bright}K | FRP: {frp}")

        image_path = image_map.get(hotspot_idx, None)
        method_used = "N/A"

        if image_path is None:
            print(f"  Image: MISSING - using fallback")
            label, conf = classify_by_brightness(bright)
            method_used = "Fallback (no image)"
        elif classifier is not None:
            label, conf = classify_image(classifier, image_path)
            if label is None:
                print(f"  Model failed - using fallback")
                label, conf = classify_by_brightness(bright)
                method_used = "Fallback (model error)"
            else:
                method_used = "AI Model (ViT)"
        else:
            label, conf = classify_by_brightness(bright)
            method_used = "Fallback (no model)"

        # Mark low-confidence predictions
        confidence_note = ""
        if conf < CONFIDENCE_THRESHOLD:
            confidence_note = " [LOW CONFIDENCE]"

        print(f"  Result: {label} ({conf:.1%} confidence) "
              f"via {method_used}{confidence_note}\n")

        results.append({
            "hotspot_id": hotspot_idx,
            "latitude": lat,
            "longitude": lon,
            "acq_date": date,
            "bright_ti4": bright,
            "frp": frp,
            "image_path": image_path if image_path else "MISSING",
            "classification": label,
            "confidence": round(conf, 4),
            "method": method_used
        })

    # ─── Save Results CSV ─────────────────────────────────────────
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Results saved to '{OUTPUT_CSV}'\n")

    # ─── Print Summary Table ──────────────────────────────────────
    fire_count = sum(1 for r in results if r["classification"] == "Fire")
    no_fire_count = sum(1 for r in results if r["classification"] == "No Fire")
    ai_count = sum(1 for r in results if "AI" in r["method"])

    print("=" * 60)
    print("   CLASSIFICATION SUMMARY")
    print("=" * 60)
    summary_lines = [
        f"Total hotspots analyzed: {len(results)}",
        f"Fire detected:           {fire_count}",
        f"No fire:                 {no_fire_count}",
        f"Classified by AI model:  {ai_count}",
        f"Classified by fallback:  {len(results) - ai_count}",
        f"Average confidence:      {sum(r['confidence'] for r in results) / len(results):.1%}",
    ]
    for line in summary_lines:
        print(f"  {line}")
    print("=" * 60)

    # ─── Save Summary Report ─────────────────────────────────────
    with open(SUMMARY_FILE, "w") as f:
        f.write("FIRE DETECTION CLASSIFICATION REPORT\n")
        f.write(f"Date generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("Model: EdBianchi/vit-fire-detection (ViT)\n")
        f.write("-" * 50 + "\n\n")
        for line in summary_lines:
            f.write(line + "\n")
        f.write("\n" + "-" * 50 + "\n")
        f.write("Detailed Results:\n\n")
        for r in results:
            f.write(f"  Hotspot {r['hotspot_id']}: {r['classification']} "
                    f"({r['confidence']:.1%}) | "
                    f"({r['latitude']}, {r['longitude']}) | "
                    f"{r['method']}\n")

    print(f"\nSummary report saved to '{SUMMARY_FILE}'")

    # ─── Generate Visual Report ───────────────────────────────────
    print(f"Generating visual report...")

    cols = 4
    rows_needed = (len(results) + cols - 1) // cols
    fig, axes = plt.subplots(rows_needed, cols, figsize=(16, 4 * rows_needed))
    if rows_needed == 1:
        axes = [axes]

    for i, r in enumerate(results):
        row_idx = i // cols
        col_idx = i % cols
        ax = axes[row_idx][col_idx]

        if r["image_path"] != "MISSING":
            try:
                img = Image.open(r["image_path"]).convert("RGB")
                ax.imshow(img)
            except Exception:
                ax.text(0.5, 0.5, "Cannot\nload image",
                        ha='center', va='center', fontsize=12,
                        transform=ax.transAxes)
        else:
            ax.text(0.5, 0.5, "Image\nmissing",
                    ha='center', va='center', fontsize=12,
                    transform=ax.transAxes)

        # Color code the title
        color = "red" if r["classification"] == "Fire" else "green"
        ax.set_title(
            f"#{r['hotspot_id']}: {r['classification']} ({r['confidence']:.0%})",
            fontsize=11, fontweight='bold', color=color
        )
        ax.axis("off")

    # Hide empty subplots
    for i in range(len(results), rows_needed * cols):
        row_idx = i // cols
        col_idx = i % cols
        axes[row_idx][col_idx].axis("off")

    plt.suptitle("Fire Detection Classification Results",
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(REPORT_IMAGE, dpi=150, bbox_inches='tight')
    print(f"Visual report saved to '{REPORT_IMAGE}'")
    print("\nDone! All classifications complete.")


if __name__ == "__main__":
    main()
