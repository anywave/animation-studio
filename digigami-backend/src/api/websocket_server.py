"""
WebSocket Server for Real-time Avatar Generation
Handles client connections and generation progress updates
"""
import asyncio
import json
import base64
import cv2
import numpy as np
from datetime import datetime
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
import logging

from ..services import FaceDetector, StyleTransferService
from ..config import settings, STYLE_CONFIGS

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.generation_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Client connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Client disconnected: {session_id}")

        # Cancel any ongoing generation
        if session_id in self.generation_tasks:
            self.generation_tasks[session_id].cancel()
            del self.generation_tasks[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


class AvatarGenerator:
    """Handles the avatar generation pipeline"""

    def __init__(self):
        self.face_detector = FaceDetector()
        self.style_transfer = StyleTransferService()
        logger.info("AvatarGenerator initialized")

    async def generate(
        self,
        session_id: str,
        image_data: str,
        style: str,
        options: dict,
        progress_callback
    ) -> dict:
        """
        Generate styled avatar from image

        Args:
            session_id: Client session ID
            image_data: Base64 encoded image
            style: Style name
            options: Generation options
            progress_callback: Async callback for progress updates

        Returns:
            Generation result dict
        """
        start_time = datetime.now()

        try:
            # Stage 1: Decode image
            await progress_callback(5, "decoding", "Decoding image...")
            image = self._decode_image(image_data)
            if image is None:
                raise ValueError("Failed to decode image")

            await asyncio.sleep(0.1)  # Allow progress update to send

            # Stage 2: Face detection (optional - skip if not found for testing)
            await progress_callback(15, "detecting", "Detecting face...")
            face_data = self.face_detector.detect(image)

            if face_data is None:
                # Skip face detection for testing - use full image
                logger.warning("No face detected - using full image for style transfer")
                await progress_callback(25, "detected", "No face found - using full image")
                face_image = image
                face_dict = None
            else:
                await progress_callback(25, "detected", f"Face detected (confidence: {face_data.confidence:.0%})")
                face_image = face_data.cropped_face
                face_dict = face_data.__dict__

            await asyncio.sleep(0.1)

            # Stage 3: Prepare for style transfer
            await progress_callback(35, "preparing", "Preparing style transfer...")

            await asyncio.sleep(0.1)

            # Stage 4: Apply style transfer
            await progress_callback(45, "styling", f"Applying {STYLE_CONFIGS[style]['name']} style...")

            # Run style transfer (CPU-bound, run in executor)
            loop = asyncio.get_event_loop()
            styled_image = await loop.run_in_executor(
                None,
                lambda: self.style_transfer.transfer(
                    face_image,
                    style=style,
                    strength=options.get('strength', 0.8),
                    preserve_expression=options.get('preserveExpression', True),
                    face_data=face_dict
                )
            )

            await progress_callback(75, "refining", "Refining details...")
            await asyncio.sleep(0.2)

            # Stage 5: Post-processing
            await progress_callback(85, "finalizing", "Finalizing avatar...")

            # Apply any additional enhancements
            if options.get('enhanceDetails', True):
                styled_image = self._enhance_details(styled_image)

            await asyncio.sleep(0.1)

            # Stage 6: Encode result
            await progress_callback(95, "encoding", "Encoding result...")
            result_data = self._encode_image(styled_image)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            await progress_callback(100, "complete", "Avatar generated!")

            return {
                "success": True,
                "avatarData": result_data,
                "metadata": {
                    "style": style,
                    "processingTime": int(processing_time),
                    "model": "digigami-v1",
                    "expression": face_data.expression if face_data else "unknown",
                    "headPose": face_data.head_pose if face_data else None
                }
            }

        except asyncio.CancelledError:
            logger.info(f"Generation cancelled for session {session_id}")
            raise

        except Exception as e:
            logger.error(f"Generation error for session {session_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _decode_image(self, image_data: str) -> Optional[np.ndarray]:
        """Decode base64 image to numpy array"""
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            # Decode base64
            image_bytes = base64.b64decode(image_data)

            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)

            # Decode image
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            return image

        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return None

    def _encode_image(self, image: np.ndarray, format: str = "png") -> str:
        """Encode numpy array to base64 data URL"""
        if format == "png":
            _, buffer = cv2.imencode('.png', image)
            mime_type = "image/png"
        else:
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
            mime_type = "image/jpeg"

        base64_data = base64.b64encode(buffer).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"

    def _enhance_details(self, image: np.ndarray) -> np.ndarray:
        """Apply final detail enhancement"""
        # Subtle sharpening
        kernel = np.array([
            [0, -0.5, 0],
            [-0.5, 3, -0.5],
            [0, -0.5, 0]
        ])
        sharpened = cv2.filter2D(image, -1, kernel)

        # Blend with original (50% sharpening)
        result = cv2.addWeighted(image, 0.5, sharpened, 0.5, 0)

        return result


# Global instances
manager = ConnectionManager()
generator = AvatarGenerator()


async def handle_websocket(websocket: WebSocket, session_id: str):
    """Main WebSocket handler"""
    await manager.connect(websocket, session_id)

    try:
        # Send handshake acknowledgment
        await manager.send_message(session_id, {
            "type": "handshake_ack",
            "sessionId": session_id,
            "styles": list(STYLE_CONFIGS.keys())
        })

        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "handshake":
                # Client handshake
                await manager.send_message(session_id, {
                    "type": "handshake_ack",
                    "sessionId": session_id
                })

            elif message_type == "generate_avatar":
                # Start avatar generation
                image_data = data.get("image")
                style = data.get("style", "kingdom-hearts")
                options = data.get("options", {})

                # Validate style
                if style not in STYLE_CONFIGS:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "code": "INVALID_STYLE",
                        "message": f"Unknown style: {style}"
                    })
                    continue

                # Progress callback
                async def send_progress(percent: int, stage: str, message: str):
                    await manager.send_message(session_id, {
                        "type": "progress",
                        "percent": percent,
                        "stage": stage,
                        "message": message
                    })

                # Run generation
                result = await generator.generate(
                    session_id,
                    image_data,
                    style,
                    options,
                    send_progress
                )

                # Send result
                await manager.send_message(session_id, {
                    "type": "result",
                    **result
                })

            elif message_type == "cancel_generation":
                # Cancel ongoing generation
                if session_id in manager.generation_tasks:
                    manager.generation_tasks[session_id].cancel()
                    await manager.send_message(session_id, {
                        "type": "status",
                        "status": "cancelled"
                    })

            elif message_type == "get_styles":
                # Return available styles
                await manager.send_message(session_id, {
                    "type": "styles",
                    "styles": STYLE_CONFIGS
                })

            elif message_type == "ping":
                # Health check
                await manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)
