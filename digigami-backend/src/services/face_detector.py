"""
Face Detection Service using MediaPipe
Extracts facial landmarks and expression data
"""
import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FaceData:
    """Extracted face data from image"""
    bbox: tuple[int, int, int, int]  # x, y, width, height
    landmarks: np.ndarray  # 478 facial landmarks
    expression: dict  # Extracted expression parameters
    head_pose: dict  # Estimated head rotation
    confidence: float
    cropped_face: np.ndarray  # Cropped and aligned face region


@dataclass
class Expression:
    """Facial expression parameters"""
    smile: float  # 0-1
    left_eye_open: float  # 0-1
    right_eye_open: float  # 0-1
    left_eyebrow_raise: float  # 0-1
    right_eyebrow_raise: float  # 0-1
    mouth_open: float  # 0-1


class FaceDetector:
    """
    MediaPipe-based face detection and landmark extraction
    """

    # Key landmark indices for expression analysis
    LANDMARKS = {
        # Eyes
        'left_eye_top': 159,
        'left_eye_bottom': 145,
        'right_eye_top': 386,
        'right_eye_bottom': 374,
        # Eyebrows
        'left_eyebrow': 105,
        'right_eyebrow': 334,
        # Mouth
        'mouth_top': 13,
        'mouth_bottom': 14,
        'mouth_left': 61,
        'mouth_right': 291,
        # Nose
        'nose_tip': 4,
        # Face outline for pose estimation
        'chin': 152,
        'forehead': 10,
        'left_cheek': 234,
        'right_cheek': 454,
    }

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        logger.info("FaceDetector initialized with MediaPipe FaceMesh")

    def detect(self, image: np.ndarray) -> Optional[FaceData]:
        """
        Detect face and extract landmarks from image

        Args:
            image: BGR image as numpy array

        Returns:
            FaceData object or None if no face detected
        """
        # Convert BGR to RGB for MediaPipe
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]

        # Process image
        results = self.face_mesh.process(rgb_image)

        if not results.multi_face_landmarks:
            logger.warning("No face detected in image")
            return None

        face_landmarks = results.multi_face_landmarks[0]

        # Extract landmarks as numpy array
        landmarks = np.array([
            [lm.x * w, lm.y * h, lm.z * w]
            for lm in face_landmarks.landmark
        ])

        # Calculate bounding box
        bbox = self._calculate_bbox(landmarks, w, h)

        # Extract expression parameters
        expression = self._extract_expression(landmarks)

        # Estimate head pose
        head_pose = self._estimate_head_pose(landmarks, w, h)

        # Crop and align face
        cropped_face = self._crop_face(image, bbox, landmarks)

        return FaceData(
            bbox=bbox,
            landmarks=landmarks,
            expression=expression,
            head_pose=head_pose,
            confidence=0.95,  # MediaPipe doesn't provide explicit confidence
            cropped_face=cropped_face
        )

    def _calculate_bbox(self, landmarks: np.ndarray, w: int, h: int) -> tuple:
        """Calculate bounding box from landmarks with padding"""
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]

        x_min = int(max(0, np.min(x_coords) - 20))
        y_min = int(max(0, np.min(y_coords) - 40))
        x_max = int(min(w, np.max(x_coords) + 20))
        y_max = int(min(h, np.max(y_coords) + 20))

        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def _extract_expression(self, landmarks: np.ndarray) -> dict:
        """Extract expression parameters from landmarks"""

        def distance(idx1: int, idx2: int) -> float:
            return np.linalg.norm(landmarks[idx1] - landmarks[idx2])

        # Eye openness (ratio of vertical to horizontal distance)
        left_eye_open = distance(
            self.LANDMARKS['left_eye_top'],
            self.LANDMARKS['left_eye_bottom']
        ) / 10.0  # Normalize

        right_eye_open = distance(
            self.LANDMARKS['right_eye_top'],
            self.LANDMARKS['right_eye_bottom']
        ) / 10.0

        # Mouth openness
        mouth_open = distance(
            self.LANDMARKS['mouth_top'],
            self.LANDMARKS['mouth_bottom']
        ) / 20.0

        # Smile detection (mouth width vs face width)
        mouth_width = distance(
            self.LANDMARKS['mouth_left'],
            self.LANDMARKS['mouth_right']
        )
        face_width = distance(
            self.LANDMARKS['left_cheek'],
            self.LANDMARKS['right_cheek']
        )
        smile = min(1.0, (mouth_width / face_width) * 2.0 - 0.5)

        # Eyebrow raise (distance from eye to eyebrow)
        left_eyebrow_raise = distance(
            self.LANDMARKS['left_eyebrow'],
            self.LANDMARKS['left_eye_top']
        ) / 15.0

        right_eyebrow_raise = distance(
            self.LANDMARKS['right_eyebrow'],
            self.LANDMARKS['right_eye_top']
        ) / 15.0

        return {
            'smile': max(0, min(1, smile)),
            'left_eye_open': max(0, min(1, left_eye_open)),
            'right_eye_open': max(0, min(1, right_eye_open)),
            'mouth_open': max(0, min(1, mouth_open)),
            'left_eyebrow_raise': max(0, min(1, left_eyebrow_raise)),
            'right_eyebrow_raise': max(0, min(1, right_eyebrow_raise)),
        }

    def _estimate_head_pose(self, landmarks: np.ndarray, w: int, h: int) -> dict:
        """Estimate head pose (yaw, pitch, roll) from landmarks"""
        # Use key points for pose estimation
        nose = landmarks[self.LANDMARKS['nose_tip']]
        chin = landmarks[self.LANDMARKS['chin']]
        forehead = landmarks[self.LANDMARKS['forehead']]
        left_cheek = landmarks[self.LANDMARKS['left_cheek']]
        right_cheek = landmarks[self.LANDMARKS['right_cheek']]

        # Calculate face center
        face_center_x = (left_cheek[0] + right_cheek[0]) / 2
        face_center_y = (forehead[1] + chin[1]) / 2

        # Yaw (left-right rotation)
        yaw = (nose[0] - face_center_x) / (w / 4) * 45  # Degrees

        # Pitch (up-down rotation)
        face_height = chin[1] - forehead[1]
        nose_relative_y = (nose[1] - forehead[1]) / face_height
        pitch = (nose_relative_y - 0.4) * 60  # Degrees

        # Roll (tilt) - based on eye line angle
        left_eye = landmarks[self.LANDMARKS['left_eye_top']]
        right_eye = landmarks[self.LANDMARKS['right_eye_top']]
        roll = np.degrees(np.arctan2(
            right_eye[1] - left_eye[1],
            right_eye[0] - left_eye[0]
        ))

        return {
            'yaw': float(np.clip(yaw, -45, 45)),
            'pitch': float(np.clip(pitch, -30, 30)),
            'roll': float(np.clip(roll, -30, 30)),
        }

    def _crop_face(self, image: np.ndarray, bbox: tuple, landmarks: np.ndarray) -> np.ndarray:
        """Crop and align face region"""
        x, y, w, h = bbox

        # Add padding for hair/shoulders
        pad_top = int(h * 0.5)
        pad_bottom = int(h * 0.2)
        pad_sides = int(w * 0.3)

        img_h, img_w = image.shape[:2]

        x1 = max(0, x - pad_sides)
        y1 = max(0, y - pad_top)
        x2 = min(img_w, x + w + pad_sides)
        y2 = min(img_h, y + h + pad_bottom)

        cropped = image[y1:y2, x1:x2]

        return cropped

    def close(self):
        """Release resources"""
        self.face_mesh.close()
