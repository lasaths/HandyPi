#!/bin/bash
# HandyPi - Raspberry Pi Setup Script
# This script sets up the environment for hand tracking on Raspberry Pi

set -e  # Exit on error

echo "=========================================="
echo "HandyPi - Raspberry Pi Setup"
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
# Try to install packages, continue even if some fail (they may have different names or already be installed)
set +e  # Temporarily disable exit on error for package installation
sudo apt install -y \
    libusb-1.0-0 \
    libgcc-s1 \
    libjpeg62-turbo \
    libjbig0 \
    libstdc++6 \
    libtiff6 \
    libc6 \
    liblzma5 \
    libpng16-16t64 \
    zlib1g \
    libudev1 \
    libdc1394-25 \
    libatomic1 \
    libraw1394-11 > /dev/null 2>&1 || {
    # If bulk install fails, try installing individually to see which ones work
    echo "   Some packages may have different names, trying alternatives..."
    for pkg in libusb-1.0-0 libgcc-s1 libjpeg62-turbo libjbig0 libstdc++6 libtiff6 libc6 liblzma5 libpng16-16t64 zlib1g libudev1 libdc1394-25 libatomic1 libraw1394-11; do
        sudo apt install -y "$pkg" > /dev/null 2>&1 || true
    done
}
set -e  # Re-enable exit on error

echo "✅ MediaPipe dependencies installation completed"

# Step 3: Install Picamera2
echo ""
echo "📷 Step 3: Installing Picamera2..."
sudo apt install -y python3-picamera2 python3-opencv

# Step 4: Select Python interpreter (prefer 3.11) and verify Picamera2
echo ""
echo "🔍 Step 4: Selecting Python interpreter (prefer 3.11) and verifying Picamera2..."

PYTHON_CMD=""

# Prefer python3.11 if it exists, otherwise fall back to python3
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
    echo "   Found python3.11, using it."
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    echo "   python3.11 not found, using default python3."
else
    echo "❌ Error: No python3 interpreter found on PATH"
    exit 1
fi

PYTHON_VERSION_FULL=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION_FULL" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION_FULL" | cut -d'.' -f2)

echo "   Selected interpreter: $PYTHON_CMD (version $PYTHON_VERSION_FULL)"

# MediaPipe 0.10.18 supports up to Python 3.11
if [ "$PYTHON_MAJOR" -gt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -gt 11 ]; }; then
    echo "⚠️  $PYTHON_CMD is version $PYTHON_VERSION_FULL"
    echo "   MediaPipe 0.10.18 requires Python <= 3.11."
    echo "   Please install python3.11 (e.g. 'sudo apt install python3.11 python3.11-venv')"
    exit 1
fi

# Verify Picamera2 with the selected interpreter
if $PYTHON_CMD -c "from picamera2 import Picamera2; print('Picamera2 OK')" 2>/dev/null; then
    echo "✅ Picamera2 is available in $PYTHON_CMD"
else
    echo "❌ Error: Picamera2 not found in $PYTHON_CMD"
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

echo "   Using Python interpreter: $PYTHON_CMD"

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
    # Double-check that PYTHON_CMD still exists
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo "❌ Error: $PYTHON_CMD not found (it may have been removed)"
        echo "   Falling back to python3"
        PYTHON_CMD=python3
    fi

    echo "   Creating venv with: $PYTHON_CMD -m venv --system-site-packages .venv"
    "$PYTHON_CMD" -m venv --system-site-packages .venv
    if [ $? -eq 0 ]; then
        echo "✅ Created virtual environment with system site-packages using $PYTHON_CMD"
    else
        echo "❌ Failed to create virtual environment with $PYTHON_CMD"
        exit 1
    fi
else
    echo "✅ Using existing .venv"
fi

# Step 8: Activate venv and install dependencies
echo ""
echo "📦 Step 8: Installing Python dependencies..."
source .venv/bin/activate

# Verify Python version in venv
VENV_PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
echo "   Using Python $VENV_PYTHON_VERSION in virtual environment"

# Upgrade pip first
pip install --upgrade pip

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "   Installing from requirements.txt..."
    set +e
    # Try to install all packages, but continue even if MediaPipe fails
    pip install -r requirements.txt 2>&1 | tee /tmp/pip_install.log
    INSTALL_STATUS=$?
    set -e
    
    # Check if critical packages (non-MediaPipe) are installed
    echo ""
    echo "   Verifying package installation..."
    MISSING_PACKAGES=()
    for pkg in pika opencv-python numpy python-dotenv rich; do
        if ! python -c "import ${pkg//-/_}" 2>/dev/null; then
            MISSING_PACKAGES+=("$pkg")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        echo "   Installing missing packages: ${MISSING_PACKAGES[*]}"
        pip install "${MISSING_PACKAGES[@]}"
    fi
    
    # Check MediaPipe separately
    if ! python -c "import mediapipe" 2>/dev/null; then
        echo ""
        echo "⚠️  Warning: MediaPipe failed to install"
        echo "   This is expected with Python 3.13"
        echo "   You'll need to build MediaPipe from source (see README)"
    fi
    
    if [ $INSTALL_STATUS -eq 0 ] && [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        echo "✅ Installed all dependencies from requirements.txt"
    else
        echo "✅ Installed available dependencies (MediaPipe may need manual installation)"
    fi
else
    echo "⚠️  requirements.txt not found, installing manually..."
    set +e
    pip install opencv-python numpy pika python-dotenv rich
    pip install mediapipe==0.10.18 || echo "   MediaPipe installation failed (expected with Python 3.13)"
    set -e
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


