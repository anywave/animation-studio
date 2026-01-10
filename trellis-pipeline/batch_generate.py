#!/usr/bin/env python3
"""
Digigami Trellis Batch 3D Generator

Batch process character poses through TRELLIS.2 to generate 3D models.
Supports both local execution (24GB+ GPU) and cloud deployment (RunPod).
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Optional, List, Dict
import subprocess

# Configuration
DEFAULT_INPUT_DIR = "../characters-reference/isolated"
DEFAULT_OUTPUT_DIR = "./output"
SUPPORTED_FORMATS = ["glb", "obj", "ply"]


class TrellisGenerator:
    """Handles TRELLIS.2 model generation"""

    def __init__(self, local: bool = False, output_format: str = "glb"):
        self.local = local
        self.output_format = output_format
        self.model = None

        if local:
            self._init_local()

    def _init_local(self):
        """Initialize local TRELLIS.2 model"""
        try:
            # Check if TRELLIS is installed
            import torch

            if not torch.cuda.is_available():
                print("ERROR: CUDA not available. Local mode requires GPU.")
                sys.exit(1)

            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if gpu_mem < 20:
                print(f"WARNING: GPU has {gpu_mem:.1f}GB VRAM. TRELLIS.2 requires 24GB+")
                print("Consider using cloud mode (--cloud) instead.")

            # Import TRELLIS
            from trellis.pipelines import TrellisImageTo3DPipeline

            print("Loading TRELLIS.2 model...")
            self.model = TrellisImageTo3DPipeline.from_pretrained(
                "microsoft/TRELLIS.2-4B"
            )
            self.model.cuda()
            print("Model loaded successfully!")

        except ImportError as e:
            print(f"ERROR: TRELLIS.2 not installed. {e}")
            print("Run: pip install trellis")
            sys.exit(1)

    def generate(self, image_path: str, output_path: str) -> bool:
        """Generate 3D model from image"""
        if self.local:
            return self._generate_local(image_path, output_path)
        else:
            print(f"Cloud mode not yet implemented. Use --local with 24GB+ GPU")
            return False

    def _generate_local(self, image_path: str, output_path: str) -> bool:
        """Local generation with TRELLIS.2"""
        try:
            from PIL import Image

            # Load image
            image = Image.open(image_path).convert("RGBA")

            # Generate 3D
            outputs = self.model(
                image,
                seed=42,
                ss_guidance_strength=7.5,
                ss_sampling_steps=12,
                slat_guidance_strength=3.0,
                slat_sampling_steps=12,
            )

            # Export based on format
            if self.output_format == "glb":
                mesh = outputs['mesh'][0]
                mesh.export(output_path)
            elif self.output_format == "obj":
                mesh = outputs['mesh'][0]
                mesh.export(output_path.replace('.glb', '.obj'))
            elif self.output_format == "ply":
                gaussian = outputs['gaussian'][0]
                gaussian.save_ply(output_path.replace('.glb', '.ply'))

            return True

        except Exception as e:
            print(f"Error generating {image_path}: {e}")
            return False


def get_image_files(input_dir: str) -> List[Path]:
    """Get all PNG files from input directory"""
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    images = list(input_path.glob("*.png"))
    images.sort()
    return images


def batch_process(
    input_dir: str,
    output_dir: str,
    local: bool = False,
    output_format: str = "glb",
    skip_existing: bool = True
) -> Dict:
    """Process all images in batch"""

    # Get images
    images = get_image_files(input_dir)
    print(f"Found {len(images)} images to process")

    if len(images) == 0:
        print("No images found!")
        return {"processed": 0, "failed": 0, "skipped": 0}

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize generator
    generator = TrellisGenerator(local=local, output_format=output_format)

    # Process each image
    results = {"processed": 0, "failed": 0, "skipped": 0}
    start_time = time.time()

    for i, image_path in enumerate(images):
        output_file = output_path / f"{image_path.stem}.{output_format}"

        # Skip if exists
        if skip_existing and output_file.exists():
            print(f"[{i+1}/{len(images)}] Skipping {image_path.name} (exists)")
            results["skipped"] += 1
            continue

        print(f"[{i+1}/{len(images)}] Processing {image_path.name}...")

        success = generator.generate(str(image_path), str(output_file))

        if success:
            results["processed"] += 1
        else:
            results["failed"] += 1

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Processed: {results['processed']}, Failed: {results['failed']}, Skipped: {results['skipped']}")

    return results


def create_manifest(input_dir: str, output_dir: str) -> None:
    """Create a manifest of images to process for cloud upload"""
    images = get_image_files(input_dir)

    manifest = {
        "total_images": len(images),
        "images": [
            {
                "name": img.name,
                "stem": img.stem,
                "size_bytes": img.stat().st_size
            }
            for img in images
        ]
    }

    manifest_path = Path(output_dir) / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Created manifest at {manifest_path}")
    print(f"Total images: {len(images)}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate 3D models from character poses using TRELLIS.2"
    )

    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT_DIR,
        help=f"Input directory with PNG images (default: {DEFAULT_INPUT_DIR})"
    )

    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for 3D models (default: {DEFAULT_OUTPUT_DIR})"
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally (requires 24GB+ GPU with TRELLIS.2 installed)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=SUPPORTED_FORMATS,
        default="glb",
        help="Output format (default: glb)"
    )

    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip existing files"
    )

    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Only create manifest file (for cloud prep)"
    )

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    input_dir = (script_dir / args.input).resolve()
    output_dir = (script_dir / args.output).resolve()

    print("=" * 50)
    print("Digigami Trellis Batch 3D Generator")
    print("=" * 50)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Mode:   {'Local' if args.local else 'Cloud (not yet implemented)'}")
    print(f"Format: {args.format}")
    print("=" * 50)

    if args.manifest:
        create_manifest(str(input_dir), str(output_dir))
    else:
        if not args.local:
            print("\nCloud mode coming soon!")
            print("For now, use --local with a 24GB+ GPU")
            print("Or use deploy_runpod.py for cloud deployment")
            print("\nCreating manifest for cloud prep...")
            create_manifest(str(input_dir), str(output_dir))
        else:
            batch_process(
                str(input_dir),
                str(output_dir),
                local=args.local,
                output_format=args.format,
                skip_existing=not args.no_skip
            )


if __name__ == "__main__":
    main()
