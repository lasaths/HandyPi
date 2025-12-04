"""Main application for YOLO11 pose full-body 'pinch' (hand raise)
and RabbitMQ messaging on Raspberry Pi.
"""

import argparse
import time
from typing import Optional, Tuple

import cv2
import numpy as np
from rich.console import Console
from ultralytics import YOLO

from rabbitmq import send_pinch_trigger, send_thumb_position, setup_rabbitmq_connection

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Threshold for normalized hand-to-head distance.
# We define "pinch" as: right wrist close to head (nose), relative to shoulder width.
PINCH_SCORE_THRESHOLD = 0.7  # smaller = closer to head -> "pinch"

# Default model path – must be a YOLO11 *pose* model, e.g. yolo11n-pose.pt
YOLO_MODEL_PATH = "yolo11n-pose.pt"

# YOLO11-pose uses COCO's 17 keypoints (0-based indices in tensors):
# 0 nose
# 1 left_eye
# 2 right_eye
# 3 left_ear
# 4 right_ear
# 5 left_shoulder
# 6 right_shoulder
# 7 left_elbow
# 8 right_elbow
# 9 left_wrist
# 10 right_wrist
# 11 left_hip
# 12 right_hip
# 13 left_knee
# 14 right_knee
# 15 left_ankle
# 16 right_ankle
NOSE_IDX = 0
LEFT_SHOULDER_IDX = 5
RIGHT_SHOULDER_IDX = 6
RIGHT_WRIST_IDX = 10


# ---------------------------------------------------------------------------
# Keypoint / gesture utilities
# ---------------------------------------------------------------------------

def compute_body_scale_from_kpts(kpts: np.ndarray) -> float:
    """
    Estimate body scale as distance between shoulders.
    Fallback to 1.0 if shoulders are not valid.
    """
    if kpts.shape[0] <= max(LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX):
        return 1.0

    ls = kpts[LEFT_SHOULDER_IDX]
    rs = kpts[RIGHT_SHOULDER_IDX]

    # If shoulders collapse to 0,0 (sometimes when undetected), avoid zero scale
    scale = float(np.linalg.norm(ls - rs))
    return scale if scale > 1e-3 else 1.0


def compute_pinch_score_from_kpts(kpts: np.ndarray) -> float:
    """
    Compute a normalized 'pinch score' between right wrist and head (nose).
    Lower score -> hand closer to head -> more 'pinch-like'.

    score = dist(right_wrist, nose) / body_scale
    body_scale = distance between shoulders.
    """
    if kpts.shape[0] <= max(NOSE_IDX, RIGHT_WRIST_IDX):
        return 1e9  # effectively "no pinch"

    nose = kpts[NOSE_IDX]
    rwrist = kpts[RIGHT_WRIST_IDX]

    dist_hw = float(np.linalg.norm(rwrist - nose))
    body_scale = compute_body_scale_from_kpts(kpts)
    return dist_hw / body_scale


def get_pinch_point_from_kpts(kpts: np.ndarray) -> Tuple[int, int]:
    """
    Visual point for the 'pinch' marker.
    We use the right wrist position as the gesture point.
    """
    rwrist = kpts[RIGHT_WRIST_IDX]
    return int(rwrist[0]), int(rwrist[1])


def get_hand_position_from_kpts(kpts: np.ndarray) -> Tuple[int, int]:
    """
    Position to send instead of thumb tip (we only have wrists).
    Right wrist in pixel coordinates.
    """
    rwrist = kpts[RIGHT_WRIST_IDX]
    return int(rwrist[0]), int(rwrist[1])


def draw_target_visualization(frame: np.ndarray, point: Tuple[int, int]) -> None:
    """Draw a small target marker at the given pixel point on the frame."""
    x, y = point
    cv2.circle(frame, (x, y), 10, (0, 0, 255), 2)
    cv2.line(frame, (x - 15, y), (x + 15, y), (0, 0, 255), 1)
    cv2.line(frame, (x, y - 15), (x, y + 15), (0, 0, 255), 1)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_live(
    camera_index: int = 0,
    width: int = 640,
    height: int = 480,
    max_num_hands: int = 1,  # kept for CLI compatibility (not used directly)
    use_picamera: bool = False,
    model_path: str = YOLO_MODEL_PATH,
) -> None:
    """Run live YOLO11 pose loop with RabbitMQ messaging."""
    console = Console()

    # Load YOLO model (pose)
    console.print(f"[cyan]Loading YOLO11 pose model:[/cyan] {model_path}")
    model = YOLO(model_path)

    cap: Optional[cv2.VideoCapture] = None
    picam2 = None

    # -----------------------------------------------------------------------
    # Camera setup
    # -----------------------------------------------------------------------
    if use_picamera:
        # PiCamera2 path (matches Ultralytics Raspberry Pi example style)
        try:
            from picamera2 import Picamera2
        except ImportError:
            raise RuntimeError(
                "Picamera2 not found. Install with: sudo apt install -y python3-picamera2"
            )

        picam2 = Picamera2()
        picam2.preview_configuration.main.size = (width, height)
        picam2.preview_configuration.main.format = "RGB888"
        picam2.preview_configuration.align()
        picam2.configure("preview")
        picam2.start()
        console.print("[green]✓[/green] Using PiCamera2 (Pi camera module)")
    else:
        # USB / other camera via OpenCV
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")
        console.print(f"[green]✓[/green] Using OpenCV VideoCapture({camera_index})")

    # -----------------------------------------------------------------------
    # RabbitMQ setup
    # -----------------------------------------------------------------------
    try:
        rabbitmq_connection, rabbitmq_channel = setup_rabbitmq_connection()
        console.print("[green]✓[/green] Connected to RabbitMQ")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect to RabbitMQ: {e}")
        rabbitmq_connection = None
        rabbitmq_channel = None

    previous_time = time.time()
    fps = 0.0
    previous_pinch_state = False

    console.print("[dim]Press 'q' or ESC to quit.[/dim]")

    try:
        while True:
            # ---------------------------------------------------------------
            # Grab frame
            # ---------------------------------------------------------------
            if use_picamera:
                # PiCamera2 frame (RGB888 as in Ultralytics docs)
                frame = picam2.capture_array()
                # Convert RGB → BGR for correct OpenCV display and consistency
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                success, frame = cap.read()
                if not success:
                    console.print("[red]Failed to read frame from camera.[/red]")
                    break

            # ---------------------------------------------------------------
            # YOLO pose inference
            # ---------------------------------------------------------------
            # imgsz can be tuned; smaller for more speed on Pi
            results = model(
                frame,
                imgsz=max(width, height),
                conf=0.5,
                verbose=False,
            )

            result = results[0]
            annotated_frame = result.plot()  # draw boxes + keypoints

            # ---------------------------------------------------------------
            # Select keypoints for one instance (best by box confidence)
            # ---------------------------------------------------------------
            kpts_xy = None
            if result.keypoints is not None and len(result.keypoints) > 0:
                # (num_instances, num_kpts, 2) tensor
                kpts_all = result.keypoints.xy

                if result.boxes is not None and len(result.boxes) == len(kpts_all):
                    confs = result.boxes.conf.cpu().numpy()
                    best_idx = int(np.argmax(confs))
                else:
                    best_idx = 0

                kpts_xy = kpts_all[best_idx].cpu().numpy()

            # ---------------------------------------------------------------
            # FPS calculation
            # ---------------------------------------------------------------
            current_time = time.time()
            delta_time = current_time - previous_time
            previous_time = current_time
            if delta_time > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / delta_time) if fps > 0 else 1.0 / delta_time

            # ---------------------------------------------------------------
            # Gesture ("pinch") + RabbitMQ logic
            # ---------------------------------------------------------------
            if kpts_xy is not None and kpts_xy.shape[0] > RIGHT_WRIST_IDX:
                pinch_score = compute_pinch_score_from_kpts(kpts_xy)
                is_pinching = pinch_score < PINCH_SCORE_THRESHOLD

                # Send pinch state change
                if is_pinching != previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        send_pinch_trigger(rabbitmq_channel, is_pinching)
                    except Exception as e:
                        console.print(f"[red]Failed to send message: {e}[/red]")

                # On pinch start, send hand position (right wrist)
                if is_pinching and not previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        hand_x_px, hand_y_px = get_hand_position_from_kpts(kpts_xy)
                        frame_height, frame_width = annotated_frame.shape[:2]
                        hand_x_normalized = hand_x_px / frame_width
                        hand_y_normalized = hand_y_px / frame_height
                        # Reuse existing function name for thumb position
                        send_thumb_position(
                            rabbitmq_channel,
                            hand_x_normalized,
                            hand_y_normalized,
                        )
                    except Exception as e:
                        console.print(f"[red]Failed to send position: {e}[/red]")

                # Draw target when "pinching" (hand raised)
                if is_pinching:
                    pinch_point = get_pinch_point_from_kpts(kpts_xy)
                    draw_target_visualization(annotated_frame, pinch_point)

                previous_pinch_state = is_pinching

                pinch_status = "[green]PINCH[/green]" if is_pinching else "[dim]-----[/dim]"
                console.print(
                    f"Instance: [cyan]{0}[/cyan] | "
                    f"score: [yellow]{pinch_score:6.3f}[/yellow] | "
                    f"{pinch_status}      ",
                    end="\r",
                )
            else:
                # No person/keypoints detected – reset pinch state
                if previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        send_pinch_trigger(rabbitmq_channel, False)
                    except Exception as e:
                        console.print(f"[red]Failed to send message: {e}[/red]")
                    previous_pinch_state = False

            # ---------------------------------------------------------------
            # Draw FPS & show
            # ---------------------------------------------------------------
            cv2.putText(
                annotated_frame,
                f"{fps:.1f} FPS",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("HandyPi – YOLO11 pose full-body gesture", annotated_frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # 'q' or ESC
                break

    finally:
        # Cleanup
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        if picam2 is not None:
            picam2.stop()
        if rabbitmq_connection and not rabbitmq_connection.is_closed:
            rabbitmq_connection.close()
        console.print("\n[green]Done.[/green]")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HandyPi – Raspberry Pi YOLO11 pose full-body gesture tracking demo"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (for OpenCV VideoCapture, default: 0)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Capture width in pixels (default: 640)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Capture height in pixels (default: 480)",
    )
    parser.add_argument(
        "--max-hands",
        type=int,
        default=1,
        help="Kept for compatibility (not used)",
    )
    parser.add_argument(
        "--picamera",
        action="store_true",
        help="Use PiCamera2 (for Raspberry Pi camera modules)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=YOLO_MODEL_PATH,
        help="Path to YOLO11 pose model (default: yolo11n-pose.pt or exported variant)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for the application."""
    args = parse_args()
    run_live(
        camera_index=args.camera,
        width=args.width,
        height=args.height,
        max_num_hands=args.max_hands,
        use_picamera=args.picamera,
        model_path=args.model,
    )


if __name__ == "__main__":
    main()
