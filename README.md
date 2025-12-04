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

- Python 3.11 or higher (3.11 recommended for Raspberry Pi - piwheels has MediaPipe builds for 3.11)
- [uv](https://github.com/astral-sh/uv) package manager
- Camera/webcam connected to your system
- RabbitMQ server (local or remote)

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
     - **Set username and password**: 
       - Username: `radr`
       - Password: `radr123` (or your preferred password)
     - **Configure wireless LAN**: 
       - SSID: `radr_open_X` (where X is your Pi Kit Number)
       - Password: `radr_password`
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

1. **Update system packages:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
   This ensures your Raspberry Pi has the latest system packages and security updates.

2. **Install system dependencies for MediaPipe (Raspberry Pi only):**
   ```bash
   sudo apt install -y libusb-1.0-0 libgcc1 libjpeg62-turbo libjbig0 libstdc++6 libtiff5 libc6 liblzma5 libpng16-16 zlib1g libudev1 libdc1394-22 libatomic1 libraw1394-11
   ```
   These libraries are required for MediaPipe on Raspberry Pi.

3. **Install uv (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc  # or restart terminal
   ```

4. **Sync project dependencies:**
   ```bash
   uv sync
   ```

   This will:
   - Create a virtual environment
   - Install all Python dependencies including MediaPipe
   - On Raspberry Pi, `uv` will automatically use [piwheels.org](https://www.piwheels.org) (configured in `pyproject.toml`) to find ARM-compatible builds
   - May take several minutes on first run

   **Note:** The project is configured to:
   - Use [piwheels.org](https://www.piwheels.org) as an additional package index for ARM-compatible wheels
   - Use `unsafe-best-match` index strategy to consider versions from all indexes (piwheels may have older MediaPipe versions than PyPI)
   - This allows `uv` to find ARM-compatible wheels for Raspberry Pi, since PyPI doesn't provide ARM64 wheels for MediaPipe

### Step 5: Configure Environment Variables

1. **Create `.env` file:**
   ```bash
   nano .env
   ```

2. **Add RabbitMQ configuration:**
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

3. **Save and exit:**
   - Press `Ctrl+X`, then `Y`, then `Enter`

### Step 6: Run the Application

```bash
uv run main.py
```

**Optional arguments:**
```bash
uv run main.py --camera 0 --width 640 --height 480 --max-hands 1
```

Press `q` or `ESC` to quit.

## Installation (Local Development)

For development on your local machine (not Raspberry Pi):

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lasaths/HandyPi.git
   cd HandyPi
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root with the following variables:
   ```env
   RABBITMQ_USERNAME=your_username
   RABBITMQ_PASSWORD=your_password
   RABBITMQ_HOST=localhost
   RABBITMQ_PORT=5672
   RABBITMQ_VHOST=/
   RABBITMQ_EXCHANGE_NAME=hand_tracking
   RABBITMQ_EXCHANGE_TYPE=topic
   RABBITMQ_ROUTING_KEY_POSITION=thumb.position
   ```

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

1. **Hand Tracking**: Uses MediaPipe Hands to detect and track hand landmarks in real-time
2. **Pinch Detection**: Calculates the distance between thumb tip (landmark 4) and index finger tip (landmark 8)
3. **Message Sending**: 
   - When pinch state changes (starts or stops), a boolean trigger message is sent to RabbitMQ
   - While pinching (distance < 40px), the normalized thumb position `[x, y]` is continuously sent to RabbitMQ
4. **Visualization**: Displays hand landmarks, connections, and a target overlay when pinching

### Message Formats

The application sends two types of messages to RabbitMQ:

#### 1. Pinch Trigger Messages
Sent when pinch state changes (on/off):
- **Routing Key**: `RADr.Handout.Trigger` (hardcoded)
- **Format**: JSON boolean
- **Example**: `true` or `false`

#### 2. Thumb Position Messages
Sent continuously while pinching:
- **Routing Key**: `thumb.position` (configurable via `RABBITMQ_ROUTING_KEY_POSITION`)
- **Format**: JSON array with normalized coordinates (0.0 to 1.0)
- **Example**: `[0.5234, 0.6789]`
- **Coordinates**:
  - First value: Normalized X position (0.0 = left edge, 1.0 = right edge)
  - Second value: Normalized Y position (0.0 = top edge, 1.0 = bottom edge)

## Project Structure

```
HandyPi/
├── main.py           # Main application entry point
├── tracker.py        # Hand tracking using MediaPipe
├── rabbitmq.py       # RabbitMQ connection and messaging utilities
├── consumer.py       # Test consumer for RabbitMQ messages
├── pyproject.toml    # Project dependencies and metadata
└── README.md         # This file
```

## Dependencies

- `mediapipe>=0.10.21` (>=0.10.0 on ARM64/Raspberry Pi) - Hand tracking
- `opencv-python>=4.8.0,<4.12.0` - Camera capture and visualization (constrained to work with MediaPipe's numpy<2 requirement)
- `numpy>=1.26.4,<2` - Numerical operations (constrained by MediaPipe requirement)
- `pika>=1.3.2` - RabbitMQ client
- `python-dotenv>=1.0.0` - Environment variable management
- `rich>=14.2.0` - Enhanced console output

**Note:** MediaPipe 0.10.21 requires `numpy<2`, while OpenCV 4.12+ requires `numpy>=2`. The project uses OpenCV <4.12.0 to maintain compatibility with MediaPipe.

## Configuration

### Environment Variables

All RabbitMQ configuration is done via environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `RABBITMQ_USERNAME` | RabbitMQ username | `guest` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `guest` |
| `RABBITMQ_HOST` | RabbitMQ server host | `localhost` |
| `RABBITMQ_PORT` | RabbitMQ server port | `5672` |
| `RABBITMQ_VHOST` | Virtual host | `/` |
| `RABBITMQ_EXCHANGE_NAME` | Exchange name | `hand_tracking` |
| `RABBITMQ_EXCHANGE_TYPE` | Exchange type | `topic` |
| `RABBITMQ_ROUTING_KEY_POSITION` | Routing key for position messages | `thumb.position` |

**Note**: The pinch trigger routing key (`RADr.Handout.Trigger`) is hardcoded in the application and cannot be configured via environment variables.

### Pinch Detection Threshold

The pinch detection threshold is hardcoded in `main.py`:
```python
PINCH_DISTANCE_THRESHOLD = 40  # pixels
```

Adjust this value to change the sensitivity of pinch detection.

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

### MediaPipe Installation Issues on Raspberry Pi

**The Problem:** `uv` by default only uses PyPI, which doesn't provide ARM64 wheels for MediaPipe. Regular `pip` works on Raspberry Pi because it automatically uses [piwheels.org](https://www.piwheels.org), which provides ARM-compatible builds.

**The Solution:** This project is configured to use piwheels via the `[[tool.uv.index]]` section in `pyproject.toml`. However, **piwheels only has MediaPipe builds for Python 3.9 and 3.11**, not 3.12.

**If you're using Python 3.12 on Raspberry Pi:**

**Option 1 (Recommended): Use Python 3.11 instead**
```bash
# Install Python 3.11 if not already installed
sudo apt install python3.11 python3.11-venv

# Create a new venv with Python 3.11
rm -rf .venv
uv venv --python 3.11
uv sync
```

**Option 2: Force index strategy and try anyway**
```bash
UV_INDEX_STRATEGY=unsafe-best-match uv sync
```
This may still fail if piwheels doesn't have Python 3.12 builds.

**Option 3: Build MediaPipe from source (works with any Python version)**
```bash
# Install other dependencies first
uv sync --no-deps
source .venv/bin/activate
uv pip install "numpy>=1.26.4" "opencv-python>=4.11.0.86" "pika>=1.3.2" "python-dotenv>=1.0.0" "rich>=14.2.0"

# Build MediaPipe from source
sudo apt install -y python3-dev python3-venv protobuf-compiler cmake
git clone https://github.com/google/mediapipe.git
cd mediapipe
uv pip install -r requirements.txt
python setup.py install --link-opencv
cd ..
rm -rf mediapipe
```

**If you're using Python 3.11:**
Simply run `uv sync` - it should work automatically with piwheels.

**Verify installation:**
```bash
python -c "import mediapipe; print('MediaPipe installed successfully')"
```

**Reference:** 
- [piwheels.org MediaPipe page](https://www.piwheels.org/project/mediapipe/) - Shows available ARM builds (3.9 and 3.11 only)
- [uv Package Indexes Documentation](https://docs.astral.sh/uv/concepts/indexes/) - How uv handles multiple indexes

## Raspberry Pi Quick Reference

**Default Credentials:**
- SSH Username: `radr`
- SSH Password: `radr123` (or the password you set during SD card setup)
- Hostname: `raspberrypi.local`

**Network:**
- SSID: `radr_open_X` (X = Pi Kit Number)
- Password: `radr_password`

**RabbitMQ:**
- Username: `radr`
- Password: `radr123`

**Direct SSH Connection (alternative to VS Code):**
```bash
ssh radr@raspberrypi.local
# Password: radr123 (or the password you set during SD card setup)
```
