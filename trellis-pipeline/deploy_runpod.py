#!/usr/bin/env python3
"""
Digigami Trellis RunPod Deployment

Deploy TRELLIS.2 to RunPod cloud GPU for batch 3D generation.
Handles pod creation, file upload, processing, and download.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict

try:
    import runpod
except ImportError:
    print("RunPod SDK not installed. Run: pip install runpod")
    runpod = None

# Configuration
POD_GPU_TYPES = {
    "a100": "NVIDIA A100 80GB PCIe",
    "a100-40": "NVIDIA A100-SXM4-40GB",
    "a6000": "NVIDIA RTX A6000",
    "4090": "NVIDIA GeForce RTX 4090",
    "3090": "NVIDIA GeForce RTX 3090",
}

DEFAULT_GPU = "4090"
DEFAULT_IMAGE = "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04"

TRELLIS_SETUP_SCRIPT = """
#!/bin/bash
set -e

echo "Setting up TRELLIS.2 environment..."

# Install dependencies
pip install -q torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
pip install -q transformers diffusers accelerate
pip install -q trimesh pillow numpy

# Clone and install TRELLIS.2
if [ ! -d "TRELLIS.2" ]; then
    git clone https://github.com/microsoft/TRELLIS.2.git
    cd TRELLIS.2
    pip install -q -e .
    cd ..
fi

echo "Setup complete!"
"""

PROCESS_SCRIPT = """
#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline

def main():
    input_dir = Path("/workspace/input")
    output_dir = Path("/workspace/output")
    output_dir.mkdir(exist_ok=True)

    # Load model
    print("Loading TRELLIS.2 model...")
    model = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
    model.cuda()
    print("Model loaded!")

    # Get images
    images = sorted(input_dir.glob("*.png"))
    print(f"Processing {len(images)} images...")

    results = {"processed": [], "failed": []}

    for i, img_path in enumerate(images):
        print(f"[{i+1}/{len(images)}] {img_path.name}")
        try:
            image = Image.open(img_path).convert("RGBA")

            outputs = model(
                image,
                seed=42,
                ss_guidance_strength=7.5,
                ss_sampling_steps=12,
                slat_guidance_strength=3.0,
                slat_sampling_steps=12,
            )

            output_path = output_dir / f"{img_path.stem}.glb"
            mesh = outputs['mesh'][0]
            mesh.export(str(output_path))

            results["processed"].append(img_path.name)
            print(f"  -> {output_path.name}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results["failed"].append({"name": img_path.name, "error": str(e)})

    # Save results
    with open(output_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\\nDone! Processed: {len(results['processed'])}, Failed: {len(results['failed'])}")

if __name__ == "__main__":
    main()
"""


class RunPodDeployer:
    """Handles RunPod deployment and management"""

    def __init__(self, api_key: Optional[str] = None):
        if runpod is None:
            raise RuntimeError("RunPod SDK not installed")

        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "RunPod API key required. Set RUNPOD_API_KEY env var or use --api-key"
            )

        runpod.api_key = self.api_key
        self.pod_id = None

    def create_pod(self, gpu_type: str = DEFAULT_GPU, name: str = "digigami-trellis") -> str:
        """Create a new RunPod instance"""

        gpu_name = POD_GPU_TYPES.get(gpu_type, gpu_type)
        print(f"Creating pod with {gpu_name}...")

        pod = runpod.create_pod(
            name=name,
            image_name=DEFAULT_IMAGE,
            gpu_type_id=gpu_name,
            cloud_type="SECURE",
            volume_in_gb=50,
            container_disk_in_gb=20,
            min_vcpu_count=4,
            min_memory_in_gb=16,
        )

        self.pod_id = pod["id"]
        print(f"Pod created: {self.pod_id}")
        return self.pod_id

    def wait_for_ready(self, timeout: int = 300) -> bool:
        """Wait for pod to be ready"""
        print("Waiting for pod to be ready...")
        start = time.time()

        while time.time() - start < timeout:
            status = runpod.get_pod(self.pod_id)
            if status.get("desiredStatus") == "RUNNING" and status.get("runtime"):
                print("Pod is ready!")
                return True
            time.sleep(5)
            print(".", end="", flush=True)

        print("\nTimeout waiting for pod")
        return False

    def run_command(self, command: str) -> str:
        """Run command on pod via SSH"""
        # Note: This is a simplified version
        # Full implementation would use runpod's SSH or exec functionality
        print(f"Running: {command[:50]}...")
        # runpod.pod_ssh(self.pod_id, command)
        return ""

    def upload_files(self, local_dir: str) -> bool:
        """Upload files to pod"""
        print(f"Uploading files from {local_dir}...")
        # Implementation would use runpod's file transfer or rsync
        return True

    def download_files(self, remote_dir: str, local_dir: str) -> bool:
        """Download files from pod"""
        print(f"Downloading files to {local_dir}...")
        # Implementation would use runpod's file transfer
        return True

    def terminate_pod(self):
        """Terminate the pod"""
        if self.pod_id:
            print(f"Terminating pod {self.pod_id}...")
            runpod.terminate_pod(self.pod_id)
            print("Pod terminated")

    def get_cost_estimate(self, gpu_type: str, duration_hours: float) -> float:
        """Estimate cost for processing"""
        hourly_rates = {
            "a100": 1.89,
            "a100-40": 1.50,
            "a6000": 0.79,
            "4090": 0.74,
            "3090": 0.44,
        }
        rate = hourly_rates.get(gpu_type, 1.0)
        return rate * duration_hours


def estimate_processing_time(num_images: int) -> float:
    """Estimate processing time in hours"""
    # ~45 seconds per image on A100
    seconds_per_image = 45
    total_seconds = num_images * seconds_per_image
    return total_seconds / 3600


def main():
    parser = argparse.ArgumentParser(
        description="Deploy TRELLIS.2 to RunPod for batch 3D generation"
    )

    parser.add_argument(
        "--api-key",
        help="RunPod API key (or set RUNPOD_API_KEY env var)"
    )

    parser.add_argument(
        "--gpu",
        choices=list(POD_GPU_TYPES.keys()),
        default=DEFAULT_GPU,
        help=f"GPU type (default: {DEFAULT_GPU})"
    )

    parser.add_argument(
        "--input", "-i",
        default="../characters-reference/isolated",
        help="Input directory with PNG images"
    )

    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Output directory for 3D models"
    )

    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Only show cost estimate, don't deploy"
    )

    parser.add_argument(
        "--terminate",
        help="Terminate existing pod by ID"
    )

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    input_dir = (script_dir / args.input).resolve()
    output_dir = (script_dir / args.output).resolve()

    print("=" * 50)
    print("Digigami Trellis RunPod Deployment")
    print("=" * 50)

    # Handle terminate
    if args.terminate:
        if runpod is None:
            print("RunPod SDK not installed")
            sys.exit(1)
        runpod.api_key = args.api_key or os.environ.get("RUNPOD_API_KEY")
        runpod.terminate_pod(args.terminate)
        print(f"Terminated pod: {args.terminate}")
        return

    # Count images
    images = list(input_dir.glob("*.png")) if input_dir.exists() else []
    num_images = len(images)
    print(f"Images to process: {num_images}")

    if num_images == 0:
        print("No images found in input directory!")
        sys.exit(1)

    # Estimate
    est_hours = estimate_processing_time(num_images)
    deployer = RunPodDeployer.__new__(RunPodDeployer)
    deployer.api_key = None
    est_cost = deployer.get_cost_estimate(args.gpu, est_hours)

    print(f"\nEstimated processing time: {est_hours:.2f} hours ({est_hours * 60:.0f} minutes)")
    print(f"Estimated cost ({args.gpu}): ${est_cost:.2f}")
    print(f"GPU: {POD_GPU_TYPES[args.gpu]}")

    if args.estimate:
        print("\n(Use without --estimate to deploy)")
        return

    # Deploy
    print("\n" + "=" * 50)
    print("DEPLOYMENT")
    print("=" * 50)

    if runpod is None:
        print("\nRunPod SDK not installed!")
        print("Install with: pip install runpod")
        print("\nAlternative: Manual deployment")
        print("1. Go to https://runpod.io/console/pods")
        print(f"2. Create pod with {POD_GPU_TYPES[args.gpu]}")
        print("3. Upload images from:", input_dir)
        print("4. Run the processing script")
        print("5. Download results to:", output_dir)
        return

    try:
        deployer = RunPodDeployer(api_key=args.api_key)

        # Create pod
        pod_id = deployer.create_pod(gpu_type=args.gpu)

        # Wait for ready
        if not deployer.wait_for_ready():
            print("Failed to start pod")
            deployer.terminate_pod()
            sys.exit(1)

        print("\nPod is ready!")
        print(f"Pod ID: {pod_id}")
        print("\nNext steps (manual for now):")
        print("1. SSH into the pod")
        print("2. Upload images to /workspace/input/")
        print("3. Run the processing script")
        print("4. Download results from /workspace/output/")
        print(f"\nWhen done, terminate with: python deploy_runpod.py --terminate {pod_id}")

    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
