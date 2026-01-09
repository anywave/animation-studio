"""
Kyur Pose Isolation Script
Crops individual poses from reference sheets into separate PNG files.
"""

import os
from PIL import Image
from pathlib import Path

# Output directory for isolated poses
OUTPUT_DIR = Path(__file__).parent / "isolated"

# Define crop regions for each source image
# Format: (left, upper, right, lower) as percentages of image dimensions
# These will be converted to pixels based on actual image size

CROP_DEFINITIONS = {
    "Kyur.png": {
        "description": "3-view turnaround",
        "poses": [
            {"name": "kyur-front-apple", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "kyur-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "kyur-back-apple", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },
    "Kyur2.png": {
        "description": "5-view turnaround",
        "poses": [
            {"name": "kyur-front-apple-2", "region": (0.0, 0.0, 0.22, 1.0)},
            {"name": "kyur-front-3quarter", "region": (0.18, 0.0, 0.40, 1.0)},
            {"name": "kyur-side-2", "region": (0.38, 0.0, 0.60, 1.0)},
            {"name": "kyur-back-3quarter", "region": (0.58, 0.0, 0.80, 1.0)},
            {"name": "kyur-back-apple-2", "region": (0.78, 0.0, 1.0, 1.0)},
        ]
    },
    "Kyur4.png": {
        "description": "3 action poses",
        "poses": [
            {"name": "kyur-excited", "region": (0.0, 0.0, 0.36, 1.0)},
            {"name": "kyur-thinking", "region": (0.38, 0.0, 0.66, 1.0)},
            {"name": "kyur-pointing", "region": (0.66, 0.0, 1.0, 1.0)},
        ]
    },
}

# Primary poses for the chat system (maps to avatar_poses in soul profile)
PRIMARY_POSES = {
    "kyur-default": "kyur-front-apple",      # Default pose
    "kyur-thinking": "kyur-thinking",         # Arms crossed, contemplative
    "kyur-excited": "kyur-excited",           # Juggling apple, energetic
    "kyur-pointing": "kyur-pointing",         # Kneeling, offering apple
}


def crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image:
    """Crop image to non-transparent content with optional padding."""
    # Get the bounding box of non-transparent pixels
    bbox = img.getbbox()
    if bbox:
        # Add padding
        left = max(0, bbox[0] - padding)
        upper = max(0, bbox[1] - padding)
        right = min(img.width, bbox[2] + padding)
        lower = min(img.height, bbox[3] + padding)
        return img.crop((left, upper, right, lower))
    return img


def isolate_poses(source_dir: Path, output_dir: Path, auto_crop: bool = True):
    """Extract individual poses from reference sheets."""
    output_dir.mkdir(exist_ok=True)

    extracted = []

    for filename, config in CROP_DEFINITIONS.items():
        source_path = source_dir / filename

        if not source_path.exists():
            print(f"  [SKIP] {filename} not found")
            continue

        print(f"\nProcessing {filename} ({config['description']})...")

        # Load source image
        img = Image.open(source_path)
        width, height = img.size
        print(f"  Source size: {width}x{height}")

        for pose in config["poses"]:
            name = pose["name"]
            region = pose["region"]

            # Convert percentage to pixels
            left = int(region[0] * width)
            upper = int(region[1] * height)
            right = int(region[2] * width)
            lower = int(region[3] * height)

            # Crop the region
            cropped = img.crop((left, upper, right, lower))

            # Auto-crop to content (remove excess transparency)
            if auto_crop:
                cropped = crop_to_content(cropped, padding=20)

            # Save
            output_path = output_dir / f"{name}.png"
            cropped.save(output_path, "PNG", optimize=True)

            print(f"  [OK] {name}.png ({cropped.width}x{cropped.height})")
            extracted.append(name)

    return extracted


def create_primary_poses(output_dir: Path):
    """Create symlinks or copies for primary chat poses."""
    print("\nCreating primary pose files...")

    for primary_name, source_name in PRIMARY_POSES.items():
        source_path = output_dir / f"{source_name}.png"
        primary_path = output_dir / f"{primary_name}.png"

        if not source_path.exists():
            print(f"  [SKIP] {source_name}.png not found")
            continue

        if primary_name == source_name:
            print(f"  [OK] {primary_name}.png (same as source)")
            continue

        # Copy the file (more portable than symlinks on Windows)
        img = Image.open(source_path)
        img.save(primary_path, "PNG", optimize=True)
        print(f"  [OK] {primary_name}.png -> {source_name}.png")


def generate_preview(output_dir: Path):
    """Generate a preview grid of all isolated poses."""
    poses = list(output_dir.glob("kyur-*.png"))

    if not poses:
        print("\nNo poses found for preview")
        return

    # Load all poses and convert to RGBA
    images = []
    for pose_path in sorted(poses):
        img = Image.open(pose_path).convert("RGBA")
        images.append((pose_path.stem, img))

    # Calculate grid size
    max_height = max(img.height for _, img in images)
    total_width = sum(img.width for _, img in images) + (len(images) - 1) * 20

    # Create preview canvas
    preview = Image.new("RGBA", (total_width, max_height + 40), (30, 30, 40, 255))

    # Paste poses with alpha compositing
    x_offset = 0
    for name, img in images:
        # Center vertically
        y_offset = (max_height - img.height) // 2
        # Use alpha_composite for proper transparency handling
        temp = Image.new("RGBA", preview.size, (0, 0, 0, 0))
        temp.paste(img, (x_offset, y_offset))
        preview = Image.alpha_composite(preview, temp)
        x_offset += img.width + 20

    # Save preview
    preview_path = output_dir / "_preview.png"
    preview.save(preview_path, "PNG")
    print(f"\nPreview saved: {preview_path}")


def main():
    print("=" * 50)
    print("KYUR POSE ISOLATION SCRIPT")
    print("=" * 50)

    source_dir = Path(__file__).parent
    output_dir = OUTPUT_DIR

    print(f"\nSource: {source_dir}")
    print(f"Output: {output_dir}")

    # Extract poses
    extracted = isolate_poses(source_dir, output_dir, auto_crop=True)

    # Create primary poses for chat system
    create_primary_poses(output_dir)

    # Generate preview
    generate_preview(output_dir)

    print("\n" + "=" * 50)
    print(f"DONE! Extracted {len(extracted)} poses")
    print("=" * 50)

    # Print usage info
    print("\nFor the chat system, use these files:")
    for primary_name in PRIMARY_POSES.keys():
        print(f"  - isolated/{primary_name}.png")


if __name__ == "__main__":
    main()
