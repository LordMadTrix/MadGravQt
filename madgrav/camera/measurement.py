"""
Object detection and real-world size measurement module for MadGrav.

Provides contour detection, pixel-to-mm homography conversion, physical dimension
measurements, and pluggable deep learning segmentation model hooks (YOLO-seg / SAM).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from madgrav.camera.autocal import transform_pixel_to_mm, transform_mm_to_pixel


@dataclass
class DetectedObject:
    """Represents an object detected in camera frame with physical measurements in mm."""

    contour_px: np.ndarray  # Nx2 float/int pixel coordinates
    contour_mm: np.ndarray  # Nx2 float mm coordinates
    bounding_box_mm: Tuple[float, float, float, float]  # (min_x, min_y, width, height) in mm
    rotated_box_mm: Tuple[Tuple[float, float], Tuple[float, float], float]  # ((cx, cy), (w, h), angle)
    area_mm2: float  # Area in square millimeters
    perimeter_mm: float  # Perimeter in millimeters
    centroid_mm: Tuple[float, float]  # (cx, cy) in mm


class BaseSegmentationModel(ABC):
    """
    Abstract interface for pluggable segmentation models (e.g. YOLO-seg, SAM, ONNX models).
    """

    @abstractmethod
    def predict_masks(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Given an input image (BGR uint8 array), return a list of binary masks (uint8 2D arrays).
        Each mask corresponds to one detected object (255 for foreground, 0 for background).
        """
        pass


def detect_objects(
    image: np.ndarray,
    homography_matrix: np.ndarray,
    min_area_mm2: float = 10.0,
    threshold_method: str = "otsu",
    blur_size: int = 5,
    seg_model: Optional[BaseSegmentationModel] = None,
) -> List[DetectedObject]:
    """
    Detect objects in an image and calculate their real-world mm measurements using homography.

    :param image: Input image (BGR or Grayscale)
    :param homography_matrix: 3x3 homography matrix (pixel -> bed mm)
    :param min_area_mm2: Minimum object area in mm² to filter noise
    :param threshold_method: 'otsu', 'adaptive', or 'canny'
    :param blur_size: Kernel size for Gaussian blur (must be odd)
    :param seg_model: Optional instance of BaseSegmentationModel (YOLO-seg / SAM)
    :return: List of DetectedObject instances
    """
    if image is None or homography_matrix is None:
        return []

    H = np.asarray(homography_matrix, dtype=np.float64)
    raw_contours = []

    if seg_model is not None:
        # Use deep learning segmentation model
        masks = seg_model.predict_masks(image)
        for mask in masks:
            if mask is None or mask.size == 0:
                continue
            cnts, _ = cv2.findContours(
                mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            raw_contours.extend(cnts)
    else:
        # Classic OpenCV image processing pipeline
        gray = image
        if gray.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if blur_size > 0:
            ksize = blur_size if blur_size % 2 == 1 else blur_size + 1
            gray = cv2.GaussianBlur(gray, (ksize, ksize), 0)

        method = str(threshold_method).lower()
        if method == "adaptive":
            thresh = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                11,
                2,
            )
        elif method == "canny":
            thresh = cv2.Canny(gray, 50, 150)
        else:  # Default to Otsu's thresholding
            _, thresh = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

        cnts, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        raw_contours.extend(cnts)

    detected_objects = []

    for cnt in raw_contours:
        if len(cnt) < 3:
            continue

        cnt_px = cnt.reshape(-1, 2).astype(np.float64)
        cnt_mm = transform_pixel_to_mm(cnt_px, H)

        # Compute polygon area in mm²
        area_mm2 = float(cv2.contourArea(cnt_mm.astype(np.float32)))
        if area_mm2 < min_area_mm2:
            continue

        # Perimeter in mm
        perimeter_mm = float(cv2.arcLength(cnt_mm.astype(np.float32), True))

        # Axis-aligned bounding box in mm (min_x, min_y, width, height)
        min_x = float(np.min(cnt_mm[:, 0]))
        max_x = float(np.max(cnt_mm[:, 0]))
        min_y = float(np.min(cnt_mm[:, 1]))
        max_y = float(np.max(cnt_mm[:, 1]))
        width_mm = max_x - min_x
        height_mm = max_y - min_y
        bbox_mm = (min_x, min_y, width_mm, height_mm)

        # Minimum area rotated rectangle in mm
        rect = cv2.minAreaRect(cnt_mm.astype(np.float32))
        (cx_mm, cy_mm), (rw_mm, rh_mm), angle = rect
        rot_box_mm = ((float(cx_mm), float(cy_mm)), (float(rw_mm), float(rh_mm)), float(angle))

        # Centroid in mm
        M = cv2.moments(cnt_mm.astype(np.float32))
        if M["m00"] != 0:
            centroid_mm = (float(M["m10"] / M["m00"]), float(M["m01"] / M["m00"]))
        else:
            centroid_mm = (float(cx_mm), float(cy_mm))

        detected_objects.append(
            DetectedObject(
                contour_px=cnt_px,
                contour_mm=cnt_mm,
                bounding_box_mm=bbox_mm,
                rotated_box_mm=rot_box_mm,
                area_mm2=area_mm2,
                perimeter_mm=perimeter_mm,
                centroid_mm=centroid_mm,
            )
        )

    return detected_objects


def draw_object_measurements(
    image: np.ndarray,
    objects: List[DetectedObject],
    homography_matrix: Optional[np.ndarray] = None,
    color_contour=(0, 255, 0),
    color_text=(0, 255, 255),
    thickness=2,
) -> np.ndarray:
    """
    Draw detected object contours and physical mm size labels on the image.

    :param image: Input image (BGR uint8)
    :param objects: List of DetectedObject instances
    :param homography_matrix: Optional 3x3 homography matrix (for inverse mapping if needed)
    :param color_contour: Contour line color BGR
    :param color_text: Text label color BGR
    :param thickness: Line thickness
    :return: Annotated BGR copy of image
    """
    output = image.copy()
    if output.ndim == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)

    for obj in objects:
        pts_px = obj.contour_px.astype(np.int32).reshape(-1, 1, 2)
        cv2.drawContours(output, [pts_px], -1, color_contour, thickness)

        # Centroid in px for label position
        c_px = np.mean(obj.contour_px, axis=0).astype(np.int32)
        _, _, w_mm, h_mm = obj.bounding_box_mm

        label = f"{w_mm:.1f}x{h_mm:.1f}mm"
        cv2.putText(
            output,
            label,
            (c_px[0] - 20, c_px[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color_text,
            1,
            cv2.LINE_AA,
        )

    return output
