"""Main application for hand tracking and RabbitMQ messaging."""
import argparse
import time

import cv2
from rich.console import Console

from rabbitmq import send_pinch_trigger, send_thumb_position, setup_rabbitmq_connection
from tracker import (
    HandTracker,
    compute_pinch_distance,
    get_pinch_point,
    get_thumb_tip_position,
    draw_target_visualization,
)

PINCH_DISTANCE_THRESHOLD = 40


def run_live(
    camera_index: int = 0,
    width: int = 640,
    height: int = 480,
    max_num_hands: int = 1,
) -> None:
    """Run live hand tracking loop with RabbitMQ messaging."""
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}")

    console = Console()
    tracker = HandTracker(max_num_hands=max_num_hands)
    
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
            success, frame = cap.read()
            if not success:
                console.print("[red]Failed to read frame from camera.[/red]")
                break

            tracked_hands = tracker.process(frame)
            tracker.draw_on_frame(frame, tracked_hands)

            current_time = time.time()
            delta_time = current_time - previous_time
            previous_time = current_time
            if delta_time > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / delta_time) if fps > 0 else 1.0 / delta_time

            if tracked_hands:
                hand = tracked_hands[0]
                pinch_distance = compute_pinch_distance(hand)
                is_pinching = pinch_distance < PINCH_DISTANCE_THRESHOLD
                
                if is_pinching != previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        send_pinch_trigger(rabbitmq_channel, is_pinching)
                    except Exception as e:
                        console.print(f"[red]Failed to send message: {e}[/red]")
                
                if is_pinching and not previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        thumb_x_px, thumb_y_px = get_thumb_tip_position(hand)
                        frame_height, frame_width = frame.shape[:2]
                        thumb_x_normalized = thumb_x_px / frame_width
                        thumb_y_normalized = thumb_y_px / frame_height
                        send_thumb_position(rabbitmq_channel, thumb_x_normalized, thumb_y_normalized)
                    except Exception as e:
                        console.print(f"[red]Failed to send position: {e}[/red]")
                
                if is_pinching:
                    pinch_point = get_pinch_point(hand)
                    draw_target_visualization(frame, pinch_point)
                
                previous_pinch_state = is_pinching
                
                pinch_status = "[green]PINCH[/green]" if is_pinching else "[dim]-----[/dim]"
                console.print(
                    f"Hand: [cyan]{hand.handedness:5s}[/cyan] | "
                    f"pinch: [yellow]{pinch_distance:6.1f}px[/yellow] | "
                    f"{pinch_status}      ",
                    end="\r",
                )
            else:
                if previous_pinch_state and rabbitmq_channel is not None:
                    try:
                        send_pinch_trigger(rabbitmq_channel, False)
                    except Exception as e:
                        console.print(f"[red]Failed to send message: {e}[/red]")
                    previous_pinch_state = False

            cv2.putText(
                frame,
                f"{fps:.1f} FPS",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("HighPiFive – finger tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        if rabbitmq_connection and not rabbitmq_connection.is_closed:
            rabbitmq_connection.close()
        console.print("\n[green]Done.[/green]")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="HighPiFive – simple Raspberry Pi hand + finger tracking demo"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0)",
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
        help="Maximum number of hands to track (default: 1)",
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
    )


if __name__ == "__main__":
    main()
