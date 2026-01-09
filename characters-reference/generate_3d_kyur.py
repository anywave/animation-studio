"""
Kyur 3D Character Generation Script

Generates a 3D model from the isolated Kyur character poses.
Requires a Tripo3D or Meshy API key.

Usage:
    python generate_3d_kyur.py --api-key YOUR_TRIPO3D_KEY

Or via the backend API:
    curl -X POST http://localhost:8765/api/3d/generate-character \
        -F "poses_dir=./isolated" \
        -F "character_name=kyur"
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "digigami-backend" / "src"))


async def generate_kyur_3d(api_key: str, backend: str = "tripo3d"):
    """Generate 3D model of Kyur from isolated poses."""
    from services.generation_3d import (
        Generation3DService,
        Generation3DBackend,
        create_3d_service
    )

    # Setup paths
    poses_dir = Path(__file__).parent / "isolated"
    output_dir = Path(__file__).parent / "3d_output"
    output_dir.mkdir(exist_ok=True)

    print("=" * 50)
    print("KYUR 3D CHARACTER GENERATION")
    print("=" * 50)
    print(f"\nPoses directory: {poses_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Backend: {backend}")

    # Check for isolated poses
    if not poses_dir.exists():
        print("\n[ERROR] Isolated poses not found!")
        print("Run isolate_poses.py first to extract character poses.")
        return

    # List available poses
    poses = list(poses_dir.glob("kyur-*.png"))
    print(f"\nFound {len(poses)} Kyur poses:")
    for pose in sorted(poses):
        print(f"  - {pose.name}")

    # Create 3D service
    if backend == "tripo3d":
        service = create_3d_service(tripo3d_key=api_key, output_dir=str(output_dir))
    else:
        service = create_3d_service(meshy_key=api_key, output_dir=str(output_dir))

    def progress_callback(progress: float, message: str):
        bar_len = 30
        filled = int(bar_len * progress / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r[{bar}] {progress:.1f}% - {message}", end="", flush=True)

    print("\n\nStarting 3D generation...")
    print("-" * 50)

    try:
        result = await service.generate_character_from_poses(
            poses_dir,
            character_name="kyur",
            progress_callback=progress_callback
        )

        print("\n" + "-" * 50)

        if result.status.value == "completed":
            print("\n[SUCCESS] 3D model generated!")
            print(f"\nModel URL: {result.model_url}")
            print(f"Thumbnail: {result.thumbnail_url}")
            print(f"Local file: {result.metadata.get('local_path')}")
        else:
            print(f"\n[FAILED] Generation failed: {result.error}")

    except ValueError as e:
        print(f"\n[ERROR] {e}")
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")
        raise
    finally:
        await service.close()

    print("\n" + "=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Generate 3D Kyur character model")
    parser.add_argument(
        "--api-key",
        default=os.getenv("DIGIGAMI_TRIPO3D_API_KEY"),
        help="Tripo3D or Meshy API key (or set DIGIGAMI_TRIPO3D_API_KEY env var)"
    )
    parser.add_argument(
        "--backend",
        choices=["tripo3d", "meshy"],
        default="tripo3d",
        help="3D generation backend to use"
    )
    args = parser.parse_args()

    if not args.api_key:
        print("[ERROR] API key required!")
        print("\nUsage:")
        print("  python generate_3d_kyur.py --api-key YOUR_API_KEY")
        print("\nOr set environment variable:")
        print("  export DIGIGAMI_TRIPO3D_API_KEY=your_key")
        print("\nGet an API key from:")
        print("  - Tripo3D: https://www.tripo3d.ai/")
        print("  - Meshy: https://www.meshy.ai/")
        sys.exit(1)

    asyncio.run(generate_kyur_3d(args.api_key, args.backend))


if __name__ == "__main__":
    main()
