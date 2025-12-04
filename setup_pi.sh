#!/bin/bash
# HandyPi (HighPiFive) - Raspberry Pi Setup Script
# This script sets up the environment for hand tracking on Raspberry Pi

set -e  # Exit on error

echo "=========================================="
echo "HandyPi (HighPiFive) - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system packages
echo "📦 Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install MediaPipe dependencies
echo ""
echo "📦 Step 2: Installing MediaPipe dependencies..."
sudo apt install -y \
    libusb-1.0-0 \
    libgcc1 \
    libjpeg62-turbo \
    libjbig0 \
    libstdc++6 \
    libtiff5 \
    libc6 \
    liblzma5 \
    libpng16-16 \
    zlib1g \
    libudev1 \
    libdc1394-22 \
    libatomic1 \
    libraw1394-11

# Step 3: Install Picamera2
echo ""
echo "📷 Step 3: Installing Picamera2..."
sudo apt install -y python3-picamera2 python3-opencv

# Step 4: Verify Picamera2 in system Python
echo ""
echo "🔍 Step 4: Verifying Picamera2 installation..."
if python3 -c "from picamera2 import Picamera2; print('Picamera2 OK')" 2>/dev/null; then
    echo "✅ Picamera2 is available in system Python"
else
    echo "❌ Error: Picamera2 not found in system Python"
    echo "   Try: sudo apt install -y python3-picamera2"
    exit 1
fi

# Step 5: Grant camera permissions
echo ""
echo "🔐 Step 5: Setting up camera permissions..."
if ! groups | grep -q video; then
    sudo usermod -a -G video $USER
    echo "✅ Added user '$USER' to 'video' group"
    echo "   ⚠️  You may need to log out and back in for this to take effect"
else
    echo "✅ User '$USER' is already in 'video' group"
fi

# Step 6: Check if camera is enabled
echo ""
echo "🔍 Step 6: Checking camera interface..."
if [ -f /boot/config.txt ]; then
    if grep -q "^start_x=1" /boot/config.txt || grep -q "^camera_auto_detect=1" /boot/config.txt; then
        echo "✅ Camera interface appears to be enabled"
    else
        echo "⚠️  Camera interface may not be enabled"
        echo "   Run: sudo raspi-config → Interface Options → Camera → Enable"
    fi
else
    echo "⚠️  Could not check camera configuration"
fi

# Step 7: Create virtual environment with system site-packages
echo ""
echo "🐍 Step 7: Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Existing .venv directory found"
    read -p "Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
        echo "✅ Removed existing .venv"
    else
        echo "⚠️  Keeping existing .venv (may cause issues if created without --system-site-packages)"
    fi
fi

if [ ! -d ".venv" ]; then
    python3 -m venv --system-site-packages .venv
    echo "✅ Created virtual environment with system site-packages"
else
    echo "✅ Using existing .venv"
fi

# Step 8: Activate venv and install dependencies
echo ""
echo "📦 Step 8: Installing Python dependencies..."
source .venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Installed dependencies from requirements.txt"
else
    echo "⚠️  requirements.txt not found, installing manually..."
    pip install mediapipe==0.10.18 opencv-python numpy pika python-dotenv rich
fi

# Step 9: Verify Picamera2 in venv
echo ""
echo "🔍 Step 9: Verifying Picamera2 in virtual environment..."
if python -c "from picamera2 import Picamera2; print('Picamera2 OK')" 2>/dev/null; then
    echo "✅ Picamera2 is accessible in virtual environment"
else
    echo "❌ Error: Picamera2 not accessible in virtual environment"
    echo "   The venv may not have been created with --system-site-packages"
    exit 1
fi

# Step 10: Summary
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. If you were added to the 'video' group, log out and back in"
echo "2. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo "3. Run the application:"
echo "   python main.py --picamera"
echo ""
echo "⚠️  Important: Use 'python main.py' (not 'uv run main.py')"
echo "   to ensure the venv with system site-packages is used"
echo ""


