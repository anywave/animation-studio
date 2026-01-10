"""
Spritesheet Generator for Digigami Characters

Creates spritesheets from isolated character poses with JSON metadata
for use in game engines and animation frameworks.
"""

import json
from pathlib import Path
from PIL import Image


def create_spritesheet(
    poses_dir: Path,
    output_dir: Path,
    character_name: str = "kyur",
    columns: int = 4,
    padding: int = 0,
    normalize_size: bool = True
):
    """
    Create a spritesheet from isolated character poses.

    Args:
        poses_dir: Directory containing isolated pose PNGs
        output_dir: Output directory for spritesheet and JSON
        character_name: Character name prefix for files
        columns: Number of columns in the spritesheet grid
        padding: Padding between sprites in pixels
        normalize_size: If True, resize all sprites to match the largest
    """
    output_dir.mkdir(exist_ok=True)

    # Find all poses (exclude preview)
    pose_files = sorted([
        f for f in poses_dir.glob(f"{character_name}-*.png")
        if not f.name.startswith("_")
    ])

    if not pose_files:
        print(f"No poses found for '{character_name}' in {poses_dir}")
        return None

    print(f"Found {len(pose_files)} poses:")
    for f in pose_files:
        print(f"  - {f.name}")

    # Load all images
    images = []
    for pose_file in pose_files:
        img = Image.open(pose_file).convert("RGBA")
        images.append({
            "name": pose_file.stem,
            "image": img,
            "original_size": img.size
        })

    # Calculate sprite dimensions
    if normalize_size:
        max_width = max(img["image"].width for img in images)
        max_height = max(img["image"].height for img in images)
        sprite_width = max_width
        sprite_height = max_height
        print(f"\nNormalized sprite size: {sprite_width}x{sprite_height}")
    else:
        # Use individual sizes (more complex metadata)
        sprite_width = max(img["image"].width for img in images)
        sprite_height = max(img["image"].height for img in images)

    # Calculate grid dimensions
    num_sprites = len(images)
    rows = (num_sprites + columns - 1) // columns

    sheet_width = columns * sprite_width + (columns - 1) * padding
    sheet_height = rows * sprite_height + (rows - 1) * padding

    print(f"Spritesheet grid: {columns}x{rows} ({num_sprites} sprites)")
    print(f"Spritesheet size: {sheet_width}x{sheet_height}")

    # Create spritesheet canvas
    spritesheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Place sprites and build metadata
    frames = {}
    animations = {
        "idle": [],
        "turnaround": [],
        "actions": []
    }

    for i, sprite_data in enumerate(images):
        row = i // columns
        col = i % columns

        x = col * (sprite_width + padding)
        y = row * (sprite_height + padding)

        img = sprite_data["image"]
        name = sprite_data["name"]

        # Center the sprite in its cell if smaller
        offset_x = (sprite_width - img.width) // 2
        offset_y = (sprite_height - img.height) // 2

        spritesheet.paste(img, (x + offset_x, y + offset_y), img)

        # Frame metadata (TexturePacker-compatible format)
        frames[name] = {
            "frame": {"x": x, "y": y, "w": sprite_width, "h": sprite_height},
            "rotated": False,
            "trimmed": offset_x > 0 or offset_y > 0,
            "spriteSourceSize": {
                "x": offset_x,
                "y": offset_y,
                "w": img.width,
                "h": img.height
            },
            "sourceSize": {"w": sprite_width, "h": sprite_height}
        }

        # Categorize for animations
        if "default" in name or "front-apple" in name:
            animations["idle"].append(name)
        if "front" in name or "side" in name or "back" in name:
            animations["turnaround"].append(name)
        if "excited" in name or "thinking" in name or "pointing" in name:
            animations["actions"].append(name)

    # Save spritesheet
    sheet_path = output_dir / f"{character_name}_spritesheet.png"
    spritesheet.save(sheet_path, "PNG", optimize=True)
    print(f"\nSpritesheet saved: {sheet_path}")

    # Build full metadata
    metadata = {
        "meta": {
            "app": "Digigami Creator Studio",
            "version": "1.0",
            "image": f"{character_name}_spritesheet.png",
            "format": "RGBA8888",
            "size": {"w": sheet_width, "h": sheet_height},
            "scale": 1
        },
        "frames": frames,
        "animations": animations
    }

    # Save JSON metadata
    json_path = output_dir / f"{character_name}_spritesheet.json"
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved: {json_path}")

    # Generate a preview with labels
    preview = spritesheet.copy()
    preview_path = output_dir / f"{character_name}_spritesheet_preview.png"
    preview.save(preview_path, "PNG")
    print(f"Preview saved: {preview_path}")

    return {
        "spritesheet": sheet_path,
        "metadata": json_path,
        "frames": len(frames),
        "size": (sheet_width, sheet_height)
    }


def main():
    print("=" * 50)
    print("DIGIGAMI SPRITESHEET GENERATOR")
    print("=" * 50)

    poses_dir = Path(__file__).parent / "isolated"
    output_dir = Path(__file__).parent / "spritesheets"

    result = create_spritesheet(
        poses_dir=poses_dir,
        output_dir=output_dir,
        character_name="kyur",
        columns=4,
        padding=0,
        normalize_size=True
    )

    if result:
        print("\n" + "=" * 50)
        print("DONE!")
        print(f"  Frames: {result['frames']}")
        print(f"  Size: {result['size'][0]}x{result['size'][1]}")
        print("=" * 50)


if __name__ == "__main__":
    main()
