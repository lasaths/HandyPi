# HandyPi (HighPiFive)

A real-time hand tracking application that detects pinch gestures using MediaPipe and sends pinch trigger states and thumb positions to RabbitMQ for distributed robotics applications.

## Features

- ✨ Real-time hand tracking using MediaPipe
- 👌 Pinch gesture detection with configurable threshold
- 📡 RabbitMQ messaging for both pinch triggers and position data
- 🎯 Visual target overlay on pinch detection
- 📊 FPS counter and live status display
- 🔧 Configurable camera settings and hand tracking parameters

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Camera/webcam
- RabbitMQ server

## Raspberry Pi Initial Setup

### Step 1: Install Raspberry Pi OS

1. **Download Raspberry Pi Imager:**
   - Download from [raspberrypi.com/software](https://www.raspberrypi.com/software/)
   - Install on your computer (Windows/Mac/Linux)

2. **Flash the SD Card:**
   - Insert SD card into your computer
   - Open Raspberry Pi Imager
   - Click "Choose OS" → Select "Raspberry Pi OS (64-bit)" (recommended)
   - Click "Choose Storage" → Select your SD card
   - Click the gear icon (⚙️) to open advanced options:
     - **Enable SSH**: Check "Enable SSH" → Use password authentication
     - **Set username and password**: Username: `radr`, Password: `radr123`
     - **Configure wireless LAN**: SSID: `radr_open_X` (X = Pi Kit Number), Password: `radr_password`
     - **Set locale settings**: Choose your timezone and keyboard layout
   - Click "Save" to apply settings
   - Click "Write" to flash the SD card (this will erase all data on the card)

3. **Boot the Raspberry Pi:**
   - Eject the SD card safely
   - Insert SD card into Raspberry Pi
   - Connect power supply to boot
   - Wait 1-2 minutes for first boot and network connection

### Step 2: Connect via VS Code Remote SSH

1. **Install VS Code Remote SSH Extension:**
   - Open VS Code on your computer
   - Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
   - Search for "Remote - SSH"
   - Install the extension by Microsoft

2. **Connect to Raspberry Pi:**
   - Press `F1` or `Ctrl+Shift+P` (Cmd+Shift+P on Mac) to open command palette
   - Type "Remote-SSH: Connect to Host"
   - Enter: `radr@raspberrypi.local`
   - If prompted, select "Linux" as the platform
   - Enter password: `radr123` (or the password you set)
   - VS Code will install the VS Code Server on the Pi (first time only)
   - You should now be connected remotely!

3. **Verify Connection:**
   - Open a terminal in VS Code (Terminal → New Terminal)
   - You should see a prompt like: `radr@raspberrypi:~ $`
   - Run: `hostname` to confirm you're on the Pi

### Step 3: Clone the Repository

1. **Open Terminal in VS Code:**
   - Terminal → New Terminal (or `Ctrl+` `)

2. **Clone the repository:**
   ```bash
   git clone https://github.com/lasaths/HandyPi.git
   cd HandyPi
   ```

### Step 4: Install Dependencies

1. **Update system packages and install MediaPipe dependencies:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y libusb-1.0-0 libgcc1 libjpeg62-turbo libjbig0 libstdc++6 libtiff5 libc6 liblzma5 libpng16-16 zlib1g libudev1 libdc1394-22 libatomic1 libraw1394-11
   ```

2. **Install uv (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

3. **Sync project dependencies:**
   ```bash
   uv sync
   ```
   Creates virtual environment and installs dependencies. On Raspberry Pi, uses MediaPipe 0.10.18 (last version with ARM64 wheels).

### Step 4: Configure Environment Variables

Create `.env` file with RabbitMQ configuration:

```env
RABBITMQ_USERNAME=radr
RABBITMQ_PASSWORD=radr123
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/
RABBITMQ_EXCHANGE_NAME=hand_tracking
RABBITMQ_EXCHANGE_TYPE=topic
RABBITMQ_ROUTING_KEY_POSITION=thumb.position
```

### Step 5: Run the Application

```bash
uv run main.py [--camera 0] [--width 640] [--height 480] [--max-hands 1]
```

Press `q` or `ESC` to quit.

## Installation (Local Development)

```bash
git clone https://github.com/lasaths/HandyPi.git
cd HandyPi
uv sync
```

Create `.env` file with your RabbitMQ credentials (see Step 4 above for format).

## Usage

### Main Application

Run the hand tracking application:
```bash
uv run main.py [--camera 0] [--width 640] [--height 480] [--max-hands 1]
```

**Command-line arguments:**
- `--camera`: Camera index (default: 0)
- `--width`: Capture width in pixels (default: 640)
- `--height`: Capture height in pixels (default: 480)
- `--max-hands`: Maximum number of hands to track (default: 1)

**Controls:**
- Press `q` or `ESC` to quit the application

### Consumer (Test Messages)

Test RabbitMQ message reception:
```bash
uv run consumer.py
```

This will listen for both pinch trigger messages and thumb position messages, displaying them in the console. Press `CTRL+C` to stop.

## How It Works

1. **Hand Tracking**: MediaPipe Hands detects hand landmarks in real-time
2. **Pinch Detection**: Distance between thumb tip (landmark 4) and index tip (landmark 8)
3. **Message Sending**:
   - Pinch state changes → boolean trigger to `RADr.Handout.Trigger`
   - While pinching (distance < 40px) → normalized thumb position `[x, y]` to `thumb.position`
4. **Visualization**: Hand landmarks, connections, and target overlay when pinching

### Message Formats

**Pinch Trigger** (state changes): `RADr.Handout.Trigger` → JSON boolean (`true`/`false`)

**Thumb Position** (while pinching): `thumb.position` → JSON array `[x, y]` (normalized 0.0-1.0)

## Project Structure

- `main.py` - Main application entry point
- `tracker.py` - Hand tracking using MediaPipe
- `rabbitmq.py` - RabbitMQ connection and messaging
- `consumer.py` - Test consumer for RabbitMQ messages
- `pyproject.toml` - Project dependencies

## Dependencies

- `mediapipe>=0.10.21` (0.10.18 on ARM64/Raspberry Pi - last version with ARM64 wheels) - Hand tracking
- `opencv-python>=4.8.0,<4.12.0` - Camera capture and visualization
- `numpy>=1.26.4,<2` - Numerical operations
- `pika>=1.3.2` - RabbitMQ client
- `python-dotenv>=1.0.0` - Environment variable management
- `rich>=14.2.0` - Enhanced console output

## Configuration

RabbitMQ settings are configured via `.env` file (see Step 4). Pinch trigger routing key (`RADr.Handout.Trigger`) is hardcoded.

Pinch detection threshold (40px) is in `main.py`:
```python
PINCH_DISTANCE_THRESHOLD = 40  # pixels
```

## Troubleshooting

### Camera Not Opening
- Ensure your camera is connected and not being used by another application
- Try different camera indices: `--camera 1`, `--camera 2`, etc.
- On Linux, you may need to grant camera permissions

### RabbitMQ Connection Failed
- Verify RabbitMQ server is running: `rabbitmqctl status`
- Check your `.env` file has correct credentials
- Ensure firewall allows connections on the configured port
- Test connection with: `uv run consumer.py`

### No Hand Detection
- Ensure good lighting conditions
- Keep hand within camera frame
- Try adjusting `--max-hands` parameter
- Check camera resolution settings

### MediaPipe Installation Issues

MediaPipe 0.10.18 is the last version with ARM64 wheels ([GitHub issue #5965](https://github.com/google-ai-edge/mediapipe/issues/5965)). If `uv sync` fails:

```bash
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install mediapipe==0.10.18
```

**Build from source (for newer versions):**
```bash
sudo apt install -y python3-dev python3-venv protobuf-compiler cmake
git clone https://github.com/google/mediapipe.git
cd mediapipe && python3 -m pip install -r requirements.txt && python setup.py install --link-opencv
cd .. && rm -rf mediapipe
```

## Quick Reference

**SSH:** `radr@raspberrypi.local` (password: `radr123`)  
**Network:** `radr_open_X` / `radr_password`  
**RabbitMQ:** `radr` / `radr123`
