"""Hand tracking using MediaPipe with visualization utilities."""
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class TrackedHand:
    """Simple container for one tracked hand."""
    handedness: str                  # "Left" or "Right"
    landmarks_px: np.ndarray         # shape (21, 2), (x, y) in pixels
    bbox: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)


class HandTracker:
    """Thin wrapper around MediaPipe Hands for real-time tracking."""

    def __init__(
        self,
        max_num_hands: int = 1,
        model_complexity: int = 0,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        """Initialize MediaPipe Hands tracker with given parameters."""
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr: np.ndarray) -> List[TrackedHand]:
        """Run hand tracking on a BGR frame and return high-level results."""
        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        results = self._hands.process(frame_rgb)
        tracked: List[TrackedHand] = []

        if not results.multi_hand_landmarks:
            return tracked

        for hand_landmarks, handedness in zip(
            results.multi_hand_landmarks, results.multi_handedness
        ):
            pts = []
            for lm in hand_landmarks.landmark:
                x_px = int(lm.x * w)
                y_px = int(lm.y * h)
                pts.append((x_px, y_px))

            landmarks_px = np.array(pts, dtype=np.int32)
            x_min = int(landmarks_px[:, 0].min())
            y_min = int(landmarks_px[:, 1].min())
            x_max = int(landmarks_px[:, 0].max())
            y_max = int(landmarks_px[:, 1].max())

            tracked.append(
                TrackedHand(
                    handedness=handedness.classification[0].label,
                    landmarks_px=landmarks_px,
                    bbox=(x_min, y_min, x_max, y_max),
                )
            )

        return tracked

    def draw_on_frame(self, frame_bgr: np.ndarray, tracked: List[TrackedHand]) -> None:
        """Draw landmarks and connections directly on the frame."""
        if not tracked:
            return

        for hand in tracked:
            for start_idx, end_idx in self._mp_hands.HAND_CONNECTIONS:
                x1, y1 = hand.landmarks_px[start_idx]
                x2, y2 = hand.landmarks_px[end_idx]
                cv2.line(
                    frame_bgr,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

            for x, y in hand.landmarks_px:
                cv2.circle(frame_bgr, (int(x), int(y)), 3, (0, 255, 255), -1)

            x_min, y_min, _, _ = hand.bbox
            cv2.putText(
                frame_bgr,
                hand.handedness,
                (x_min, max(0, y_min - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 255),
                2,
                cv2.LINE_AA,
            )

    def close(self) -> None:
        """Close the MediaPipe Hands tracker."""
        self._hands.close()


# Hand analysis utilities
def compute_pinch_distance(hand: TrackedHand) -> float:
    """Calculate distance between thumb tip (4) and index tip (8) in pixels."""
    if hand.landmarks_px.shape[0] < 9:
        return 0.0
    thumb_tip = hand.landmarks_px[4]
    index_tip = hand.landmarks_px[8]
    return float(np.linalg.norm(thumb_tip - index_tip))


def get_thumb_tip_position(hand: TrackedHand) -> Tuple[int, int]:
    """Get the thumb tip (landmark 4) position in pixels."""
    if hand.landmarks_px.shape[0] < 5:
        return (0, 0)
    thumb_tip = hand.landmarks_px[4]
    return (int(thumb_tip[0]), int(thumb_tip[1]))


def get_pinch_point(hand: TrackedHand) -> Tuple[int, int]:
    """Get the pinch point (midpoint between thumb tip and index tip) in pixels."""
    if hand.landmarks_px.shape[0] < 9:
        return (0, 0)
    thumb_tip = hand.landmarks_px[4]
    index_tip = hand.landmarks_px[8]
    pinch_x = int((thumb_tip[0] + index_tip[0]) / 2)
    pinch_y = int((thumb_tip[1] + index_tip[1]) / 2)
    return (pinch_x, pinch_y)


# Visualization utilities
def draw_target_visualization(frame_bgr: np.ndarray, center: Tuple[int, int], size: int = 30) -> None:
    """Draw a target/crosshair visualization at the specified center point."""
    x, y = center
    color = (0, 0, 255)
    thickness = 2
    
    cv2.circle(frame_bgr, (x, y), size, color, thickness, cv2.LINE_AA)
    cv2.circle(frame_bgr, (x, y), size // 3, color, thickness, cv2.LINE_AA)
    cv2.line(frame_bgr, (x - size, y), (x + size, y), color, thickness, cv2.LINE_AA)
    cv2.line(frame_bgr, (x, y - size), (x, y + size), color, thickness, cv2.LINE_AA)
