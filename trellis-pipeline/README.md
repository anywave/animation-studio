# Digigami Trellis 3D Pipeline

Batch 3D model generation from character poses using Microsoft's TRELLIS.2

## Requirements

### Hardware Options

| Option | VRAM | Cost | Notes |
|--------|------|------|-------|
| **RTX 4090** | 24GB | ~$1600 | Local, fastest |
| **RTX 3090** | 24GB | ~$900 used | Local, good option |
| **RunPod A100** | 40GB | ~$1.89/hr | Cloud, recommended |
| **Vast.ai RTX 4090** | 24GB | ~$0.40/hr | Cloud, cheapest |
| **Lambda Labs** | 24-80GB | ~$1.10/hr | Cloud, reliable |

Your current GPU: GTX 1060 (6GB) - **Not compatible**

### Software Requirements
- Python 3.10+
- CUDA 12.1+
- PyTorch 2.0+
- Linux (WSL2 works for cloud deployment scripts)

## Quick Start (Cloud)

### 1. Set up RunPod account
```bash
# Install runpod CLI
pip install runpod

# Configure API key
runpod config --api-key YOUR_KEY
```

### 2. Deploy Trellis pod
```bash
python deploy_runpod.py
```

### 3. Run batch processing
```bash
python batch_generate.py --input ../characters-reference/isolated --output ./output
```

## Local Setup (24GB+ GPU)

### 1. Clone TRELLIS.2
```bash
git clone https://github.com/microsoft/TRELLIS.2.git
cd TRELLIS.2
```

### 2. Create conda environment
```bash
conda create -n trellis python=3.10
conda activate trellis
pip install -r requirements.txt
```

### 3. Download model weights
```bash
# Weights download automatically on first run
# Or manually from: https://huggingface.co/microsoft/TRELLIS.2-4B
```

### 4. Run batch processing
```bash
python batch_generate.py --local --input ../characters-reference/isolated --output ./output
```

## Output Formats

TRELLIS.2 can export to:
- **GLB/GLTF** - Web/game ready with textures
- **OBJ** - Universal mesh format
- **PLY** - Point cloud data
- **3D Gaussians** - For Gaussian splatting renderers

## Cost Estimation

For 63 character poses:
- ~30-60 seconds per image on A100
- Total time: ~30-60 minutes
- Cloud cost: ~$1-2 total

## Troubleshooting

### "CUDA out of memory"
- Reduce batch size in config
- Use `--low-vram` flag
- Try smaller model variant

### Poor quality output
- Use higher resolution input (1024px+)
- Clean background (transparent PNG best)
- Front-facing poses work best

## Resources

- [TRELLIS.2 GitHub](https://github.com/microsoft/TRELLIS.2)
- [Hugging Face Model](https://huggingface.co/microsoft/TRELLIS.2-4B)
- [RunPod Templates](https://runpod.io/templates)
