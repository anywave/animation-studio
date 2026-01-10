"""
Digigami Character Pose Isolation Script
Crops individual poses from reference sheets into separate PNG files.

Supports: Kyur, Gwynn, Urahara, Yoroiche
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
    # ========== KYUR ==========
    "Kyur.png": {
        "description": "Kyur 3-view turnaround",
        "poses": [
            {"name": "kyur-front-apple", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "kyur-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "kyur-back-apple", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },
    "Kyur2.png": {
        "description": "Kyur 5-view turnaround",
        "poses": [
            {"name": "kyur-front-apple-2", "region": (0.0, 0.0, 0.20, 1.0)},
            {"name": "kyur-front-3quarter", "region": (0.20, 0.0, 0.40, 1.0)},
            {"name": "kyur-side-2", "region": (0.40, 0.0, 0.60, 1.0)},
            {"name": "kyur-back-3quarter", "region": (0.60, 0.0, 0.80, 1.0)},
            {"name": "kyur-back-apple-2", "region": (0.80, 0.0, 1.0, 1.0)},
        ]
    },
    "Kyur4.png": {
        "description": "Kyur 3 action poses",
        "poses": [
            {"name": "kyur-excited", "region": (0.0, 0.0, 0.36, 1.0)},
            {"name": "kyur-thinking", "region": (0.38, 0.0, 0.66, 1.0)},
            {"name": "kyur-pointing", "region": (0.66, 0.0, 1.0, 1.0)},
        ]
    },

    # ========== GWYNN ==========
    "Gwynn.png": {
        "description": "Gwynn 3-view turnaround",
        "poses": [
            {"name": "gwynn-front", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "gwynn-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "gwynn-back", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },
    "Gwynn2.png": {
        "description": "Gwynn 5-view turnaround",
        "poses": [
            {"name": "gwynn-front-2", "region": (0.0, 0.0, 0.20, 1.0)},
            {"name": "gwynn-front-3quarter", "region": (0.20, 0.0, 0.40, 1.0)},
            {"name": "gwynn-side-2", "region": (0.40, 0.0, 0.60, 1.0)},
            {"name": "gwynn-back-3quarter", "region": (0.60, 0.0, 0.80, 1.0)},
            {"name": "gwynn-back-2", "region": (0.80, 0.0, 1.0, 1.0)},
        ]
    },
    "Gwynn3.png": {
        "description": "Gwynn expressions",
        "poses": [
            {"name": "gwynn-happy", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "gwynn-neutral", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "gwynn-determined", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
    "Gwynn4.png": {
        "description": "Gwynn action poses",
        "poses": [
            {"name": "gwynn-action-1", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "gwynn-action-2", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "gwynn-action-3", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
    "Gwynn-Hades Mod.png": {
        "description": "Gwynn Hades variant",
        "poses": [
            {"name": "gwynn-hades-front", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "gwynn-hades-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "gwynn-hades-back", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },

    # ========== URAHARA ==========
    "Urahara.png": {
        "description": "Urahara 3-view turnaround",
        "poses": [
            {"name": "urahara-front", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "urahara-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "urahara-back", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },
    "Urahara2.png": {
        "description": "Urahara 5-view turnaround",
        "poses": [
            {"name": "urahara-front-2", "region": (0.0, 0.0, 0.20, 1.0)},
            {"name": "urahara-front-3quarter", "region": (0.20, 0.0, 0.40, 1.0)},
            {"name": "urahara-side-2", "region": (0.40, 0.0, 0.60, 1.0)},
            {"name": "urahara-back-3quarter", "region": (0.60, 0.0, 0.80, 1.0)},
            {"name": "urahara-back-2", "region": (0.80, 0.0, 1.0, 1.0)},
        ]
    },

    # ========== YOROICHE ==========
    "Yoroiche.png": {
        "description": "Yoroiche 3-view turnaround",
        "poses": [
            {"name": "yoroiche-front", "region": (0.0, 0.0, 0.35, 1.0)},
            {"name": "yoroiche-side", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "yoroiche-back", "region": (0.65, 0.0, 1.0, 1.0)},
        ]
    },
    "Yoroiche2.png": {
        "description": "Yoroiche 5-view turnaround",
        "poses": [
            {"name": "yoroiche-front-2", "region": (0.0, 0.0, 0.20, 1.0)},
            {"name": "yoroiche-front-3quarter", "region": (0.20, 0.0, 0.40, 1.0)},
            {"name": "yoroiche-side-2", "region": (0.40, 0.0, 0.60, 1.0)},
            {"name": "yoroiche-back-3quarter", "region": (0.60, 0.0, 0.80, 1.0)},
            {"name": "yoroiche-back-2", "region": (0.80, 0.0, 1.0, 1.0)},
        ]
    },
    "Yoroiche3.png": {
        "description": "Yoroiche expressions (half-size)",
        "poses": [
            {"name": "yoroiche-expr-1", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "yoroiche-expr-2", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "yoroiche-expr-3", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
    "Yoroiche4.png": {
        "description": "Yoroiche action poses 1",
        "poses": [
            {"name": "yoroiche-action-1", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "yoroiche-action-2", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "yoroiche-action-3", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
    "Yoroiche5.png": {
        "description": "Yoroiche action poses 2",
        "poses": [
            {"name": "yoroiche-action-4", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "yoroiche-action-5", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "yoroiche-action-6", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
    "Yoroiche6.png": {
        "description": "Yoroiche action poses 3",
        "poses": [
            {"name": "yoroiche-action-7", "region": (0.0, 0.0, 0.33, 1.0)},
            {"name": "yoroiche-action-8", "region": (0.33, 0.0, 0.67, 1.0)},
            {"name": "yoroiche-action-9", "region": (0.67, 0.0, 1.0, 1.0)},
        ]
    },
}

# Primary poses for the chat system (maps to avatar_poses in soul profile)
PRIMARY_POSES = {
    # Kyur
    "kyur-default": "kyur-front-apple",
    "kyur-thinking": "kyur-thinking",
    "kyur-excited": "kyur-excited",
    "kyur-pointing": "kyur-pointing",
    # Gwynn
    "gwynn-default": "gwynn-front",
    "gwynn-happy": "gwynn-happy",
    "gwynn-determined": "gwynn-determined",
    # Urahara
    "urahara-default": "urahara-front",
    # Yoroiche
    "yoroiche-default": "yoroiche-front",
}

# All character names
CHARACTERS = ["kyur", "gwynn", "urahara", "yoroiche"]


def crop_to_content(img: Image.Image, padding: int = 10) -> Image.Image:
    """Crop image to non-transparent content with optional padding."""
    bbox = img.getbbox()
    if bbox:
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
    by_character = {char: [] for char in CHARACTERS}

    for filename, config in CROP_DEFINITIONS.items():
        source_path = source_dir / filename

        if not source_path.exists():
            print(f"  [SKIP] {filename} not found")
            continue

        print(f"\nProcessing {filename} ({config['description']})...")

        img = Image.open(source_path)
        width, height = img.size
        print(f"  Source size: {width}x{height}")

        for pose in config["poses"]:
            name = pose["name"]
            region = pose["region"]

            left = int(region[0] * width)
            upper = int(region[1] * height)
            right = int(region[2] * width)
            lower = int(region[3] * height)

            cropped = img.crop((left, upper, right, lower))

            if auto_crop:
                cropped = crop_to_content(cropped, padding=20)

            output_path = output_dir / f"{name}.png"
            cropped.save(output_path, "PNG", optimize=True)

            print(f"  [OK] {name}.png ({cropped.width}x{cropped.height})")
            extracted.append(name)

            # Track by character
            for char in CHARACTERS:
                if name.startswith(char):
                    by_character[char].append(name)
                    break

    return extracted, by_character


def create_primary_poses(output_dir: Path):
    """Create copies for primary chat poses."""
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

        img = Image.open(source_path)
        img.save(primary_path, "PNG", optimize=True)
        print(f"  [OK] {primary_name}.png -> {source_name}.png")


def generate_preview(output_dir: Path, character: str):
    """Generate a preview grid for a specific character."""
    poses = list(output_dir.glob(f"{character}-*.png"))

    if not poses:
        print(f"\n  No poses found for {character}")
        return

    # Load all poses
    images = []
    for pose_path in sorted(poses):
        if pose_path.stem.endswith("-default"):
            continue  # Skip default aliases
        img = Image.open(pose_path).convert("RGBA")
        images.append((pose_path.stem, img))

    if not images:
        return

    # Calculate grid size
    max_height = max(img.height for _, img in images)
    total_width = sum(img.width for _, img in images) + (len(images) - 1) * 20

    # Create preview canvas
    preview = Image.new("RGBA", (total_width, max_height + 40), (30, 30, 40, 255))

    # Paste poses
    x_offset = 0
    for name, img in images:
        y_offset = (max_height - img.height) // 2
        temp = Image.new("RGBA", preview.size, (0, 0, 0, 0))
        temp.paste(img, (x_offset, y_offset))
        preview = Image.alpha_composite(preview, temp)
        x_offset += img.width + 20

    preview_path = output_dir / f"_preview_{character}.png"
    preview.save(preview_path, "PNG")
    print(f"  Preview saved: {preview_path}")


def main():
    print("=" * 50)
    print("DIGIGAMI POSE ISOLATION SCRIPT")
    print("=" * 50)

    source_dir = Path(__file__).parent
    output_dir = OUTPUT_DIR

    print(f"\nSource: {source_dir}")
    print(f"Output: {output_dir}")

    # Extract poses
    extracted, by_character = isolate_poses(source_dir, output_dir, auto_crop=True)

    # Create primary poses
    create_primary_poses(output_dir)

    # Generate preview for each character
    print("\nGenerating previews...")
    for char in CHARACTERS:
        if by_character[char]:
            generate_preview(output_dir, char)

    print("\n" + "=" * 50)
    print(f"DONE! Extracted {len(extracted)} poses total")
    for char in CHARACTERS:
        count = len(by_character[char])
        if count > 0:
            print(f"  {char.capitalize()}: {count} poses")
    print("=" * 50)


if __name__ == "__main__":
    main()
