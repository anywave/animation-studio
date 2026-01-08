"""
Style Transfer Service for Digigami Avatar Generation
Transforms photos into Kingdom Hearts / Dark Cloud 2 style avatars
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
import cv2
from pathlib import Path
from typing import Optional
import logging

from ..config import settings, STYLE_CONFIGS

logger = logging.getLogger(__name__)


class VGGFeatures(nn.Module):
    """VGG19 feature extractor for style transfer"""

    def __init__(self):
        super().__init__()
        vgg = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1).features

        # Split VGG into blocks for multi-scale features
        self.slice1 = nn.Sequential(*list(vgg.children())[:4])   # relu1_2
        self.slice2 = nn.Sequential(*list(vgg.children())[4:9])  # relu2_2
        self.slice3 = nn.Sequential(*list(vgg.children())[9:18])  # relu3_4
        self.slice4 = nn.Sequential(*list(vgg.children())[18:27]) # relu4_4
        self.slice5 = nn.Sequential(*list(vgg.children())[27:36]) # relu5_4

        # Freeze all parameters
        for param in self.parameters():
            param.requires_grad = False

    def forward(self, x):
        h1 = self.slice1(x)
        h2 = self.slice2(h1)
        h3 = self.slice3(h2)
        h4 = self.slice4(h3)
        h5 = self.slice5(h4)
        return [h1, h2, h3, h4, h5]


class StyleTransferNet(nn.Module):
    """
    Neural style transfer network for anime/game art styles
    Uses encoder-decoder architecture with AdaIN (Adaptive Instance Normalization)
    """

    def __init__(self):
        super().__init__()

        # Encoder (VGG-based)
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(128, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(256, 512, 3, padding=1),
            nn.ReLU(inplace=True),
        )

        # Style transformation layers
        self.style_transform = nn.Sequential(
            nn.Conv2d(512, 512, 3, padding=1),
            nn.InstanceNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, padding=1),
            nn.InstanceNorm2d(512),
            nn.ReLU(inplace=True),
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Conv2d(512, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),

            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),

            nn.Conv2d(128, 128, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest'),

            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 3, 3, padding=1),
            nn.Tanh(),
        )

    def forward(self, x, style_code=None):
        # Encode
        features = self.encoder(x)

        # Apply style transformation
        styled = self.style_transform(features)

        # Decode
        output = self.decoder(styled)

        return output


class AnimeStyleProcessor:
    """
    Applies anime-specific post-processing effects:
    - Edge detection for line art
    - Color quantization for cel-shading
    - Soft shading gradients
    """

    @staticmethod
    def apply_cel_shading(image: np.ndarray, levels: int = 4) -> np.ndarray:
        """Apply cel-shading effect by quantizing colors"""
        # Convert to LAB for better color handling
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Quantize L channel for shading levels
        l_channel = lab[:, :, 0]
        l_quantized = np.floor(l_channel / (256 / levels)) * (256 / levels)
        lab[:, :, 0] = l_quantized.astype(np.uint8)

        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def extract_edges(image: np.ndarray, threshold1: int = 50, threshold2: int = 150) -> np.ndarray:
        """Extract edge lines for anime-style outlines"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, threshold1, threshold2)

        # Dilate edges slightly
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        return edges

    @staticmethod
    def apply_outline(image: np.ndarray, edges: np.ndarray, color: tuple = (20, 20, 30)) -> np.ndarray:
        """Overlay edge lines on image"""
        result = image.copy()
        result[edges > 0] = color
        return result

    @staticmethod
    def enhance_colors(image: np.ndarray, saturation: float = 1.3, vibrance: float = 1.2) -> np.ndarray:
        """Enhance colors for more vibrant anime look"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)

        # Boost saturation
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)

        # Boost value (brightness) for vibrance
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * vibrance, 0, 255)

        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    @staticmethod
    def apply_soft_glow(image: np.ndarray, strength: float = 0.3) -> np.ndarray:
        """Apply soft glow effect common in anime"""
        # Create blurred version
        blurred = cv2.GaussianBlur(image, (21, 21), 0)

        # Blend with original
        result = cv2.addWeighted(image, 1.0, blurred, strength, 0)

        return result


class StyleTransferService:
    """
    Main service for transforming photos into styled avatars
    """

    def __init__(self):
        self.device = torch.device(settings.device)
        logger.info(f"StyleTransferService using device: {self.device}")

        # Initialize models
        self.vgg_features = VGGFeatures().to(self.device).eval()
        self.transfer_net = StyleTransferNet().to(self.device)
        self.anime_processor = AnimeStyleProcessor()

        # Load pretrained weights if available
        self._load_weights()

        # Image transforms
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self.denormalize = transforms.Compose([
            transforms.Normalize(mean=[0, 0, 0], std=[1/0.229, 1/0.224, 1/0.225]),
            transforms.Normalize(mean=[-0.485, -0.456, -0.406], std=[1, 1, 1])
        ])

    def _load_weights(self):
        """Load pretrained model weights if available"""
        weights_path = Path(settings.weights_dir)

        for style_name, config in STYLE_CONFIGS.items():
            model_path = weights_path / f"{config['model']}.pth"
            if model_path.exists():
                logger.info(f"Loading weights for {style_name}: {model_path}")
                # Would load style-specific weights here

        # For now, use randomly initialized weights (will be trained)
        logger.warning("No pretrained weights found, using untrained model")

    def transfer(
        self,
        image: np.ndarray,
        style: str = "kingdom-hearts",
        strength: float = 0.8,
        preserve_expression: bool = True,
        face_data: Optional[dict] = None
    ) -> np.ndarray:
        """
        Transform image to specified anime style

        Args:
            image: BGR image as numpy array
            style: Style name from STYLE_CONFIGS
            strength: Style transfer strength (0-1)
            preserve_expression: Whether to preserve facial expression
            face_data: Optional face detection data for expression preservation

        Returns:
            Styled image as numpy array
        """
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS['kingdom-hearts'])
        logger.info(f"Applying style: {style_config['name']} with strength {strength}")

        # Resize for processing
        h, w = image.shape[:2]
        target_size = settings.output_size

        # Maintain aspect ratio
        scale = target_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(image, (new_w, new_h))

        # Pad to square
        padded = self._pad_to_square(resized, target_size)

        # Convert to tensor
        rgb_image = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)

        # Apply neural style transfer
        with torch.no_grad():
            styled_tensor = self.transfer_net(tensor)

            # Blend with original based on strength
            styled_tensor = tensor * (1 - strength) + styled_tensor * strength

        # Convert back to numpy
        styled = self._tensor_to_image(styled_tensor)

        # Apply anime-specific post-processing based on style
        styled = self._apply_style_postprocess(styled, style_config)

        # Crop back to original aspect ratio
        styled = self._unpad_image(styled, new_w, new_h, target_size)

        # Resize to output size
        styled = cv2.resize(styled, (target_size, target_size))

        return styled

    def _pad_to_square(self, image: np.ndarray, target_size: int) -> np.ndarray:
        """Pad image to square with black borders"""
        h, w = image.shape[:2]
        result = np.zeros((target_size, target_size, 3), dtype=np.uint8)

        y_offset = (target_size - h) // 2
        x_offset = (target_size - w) // 2

        result[y_offset:y_offset+h, x_offset:x_offset+w] = image
        return result

    def _unpad_image(self, image: np.ndarray, orig_w: int, orig_h: int, padded_size: int) -> np.ndarray:
        """Remove padding from image"""
        h, w = image.shape[:2]

        y_offset = (h - orig_h) // 2
        x_offset = (w - orig_w) // 2

        return image[y_offset:y_offset+orig_h, x_offset:x_offset+orig_w]

    def _tensor_to_image(self, tensor: torch.Tensor) -> np.ndarray:
        """Convert tensor back to numpy image"""
        tensor = tensor.squeeze(0).cpu()

        # Denormalize
        tensor = self.denormalize(tensor)

        # Clamp and convert
        tensor = torch.clamp(tensor, 0, 1)
        image = tensor.permute(1, 2, 0).numpy()
        image = (image * 255).astype(np.uint8)

        # Convert RGB to BGR
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    def _apply_style_postprocess(self, image: np.ndarray, style_config: dict) -> np.ndarray:
        """Apply style-specific post-processing"""
        style_name = style_config.get('model', '')

        if 'kh' in style_name or 'kingdom' in style_name.lower():
            # Kingdom Hearts: Vibrant colors, soft shading, subtle outlines
            image = self.anime_processor.enhance_colors(image, saturation=1.4, vibrance=1.2)
            image = self.anime_processor.apply_soft_glow(image, strength=0.25)
            edges = self.anime_processor.extract_edges(image, threshold1=80, threshold2=180)
            image = self.anime_processor.apply_outline(image, edges, color=(40, 35, 50))

        elif 'dc' in style_name or 'dark' in style_name.lower():
            # Dark Cloud 2: Strong cel-shading, bold outlines
            image = self.anime_processor.apply_cel_shading(image, levels=5)
            image = self.anime_processor.enhance_colors(image, saturation=1.3, vibrance=1.1)
            edges = self.anime_processor.extract_edges(image, threshold1=40, threshold2=120)
            image = self.anime_processor.apply_outline(image, edges, color=(30, 25, 40))

        elif 'ghibli' in style_name.lower():
            # Ghibli: Soft colors, painterly, minimal outlines
            image = self.anime_processor.apply_soft_glow(image, strength=0.4)
            image = self.anime_processor.enhance_colors(image, saturation=1.1, vibrance=1.15)

        elif 'cel' in style_name.lower():
            # Cel Shade: Maximum cel-shading, strong outlines
            image = self.anime_processor.apply_cel_shading(image, levels=3)
            image = self.anime_processor.enhance_colors(image, saturation=1.5, vibrance=1.0)
            edges = self.anime_processor.extract_edges(image, threshold1=30, threshold2=100)
            image = self.anime_processor.apply_outline(image, edges, color=(10, 10, 20))

        return image

    def get_available_styles(self) -> dict:
        """Return available style configurations"""
        return STYLE_CONFIGS
