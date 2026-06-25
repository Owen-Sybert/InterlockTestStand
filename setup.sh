#!/usr/bin/env bash
set -e

echo "======================================"
echo " InterlockTestStand first-time setup"
echo "======================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="teststandgui"

echo ""
echo "[1/6] Installing Raspberry Pi system packages..."
sudo apt update
sudo apt install -y \
    git \
    build-essential \
    cmake \
    make \
    gdb \
    pkg-config \
    python3-pip \
    libgl1 \
    libegl1 \
    libxcb-cursor0 \
    libxkbcommon-x11-0

echo ""
echo "[2/6] Adding user to dialout group for Teknic USB serial access..."
sudo usermod -aG dialout "$USER"

echo ""
echo "[3/6] Creating/updating conda environment..."
if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: conda was not found."
    echo "Install Miniconda/Miniforge first, then re-run ./setup.sh"
    exit 1
fi

conda env update --file "$PROJECT_ROOT/environment.yml" --prune

echo ""
echo "[4/6] Looking for Teknic sFoundation..."
TEKNIC_DIR=""

if [ -d "$PROJECT_ROOT/Linux_Software/sFoundation" ]; then
    TEKNIC_DIR="$PROJECT_ROOT/Linux_Software/sFoundation"
elif [ -d "$HOME/Desktop/Linux_Software/sFoundation" ]; then
    TEKNIC_DIR="$HOME/Desktop/Linux_Software/sFoundation"
elif [ -d "$HOME/Linux_Software/sFoundation" ]; then
    TEKNIC_DIR="$HOME/Linux_Software/sFoundation"
fi

if [ -z "$TEKNIC_DIR" ]; then
    echo "WARNING: Teknic sFoundation folder was not found."
    echo "Expected one of:"
    echo "  $PROJECT_ROOT/Linux_Software/sFoundation"
    echo "  $HOME/Desktop/Linux_Software/sFoundation"
    echo "  $HOME/Linux_Software/sFoundation"
    echo ""
    echo "GUI dependencies are installed, but Teknic runtime build may fail until sFoundation is present."
else
    echo "Found Teknic sFoundation at: $TEKNIC_DIR"
    export TEKNIC_SDK_DIR="$TEKNIC_DIR"

    echo ""
    echo "[5/6] Building/installing Teknic sFoundation..."
    cd "$TEKNIC_DIR"
    make || {
        echo "ERROR: Teknic sFoundation make failed."
        exit 1
    }

    if [ -f "libsFoundation20.so" ]; then
        sudo cp libsFoundation20.so /usr/local/lib/
    fi

    if [ -f "MNuserDriver20.xml" ]; then
        sudo cp MNuserDriver20.xml /usr/local/lib/
    fi

    sudo ldconfig

    if [ -d "$TEKNIC_DIR/../SDK_Examples/HelloWorld" ]; then
        echo ""
        echo "Building Teknic HelloWorld example..."
        cd "$TEKNIC_DIR/../SDK_Examples/HelloWorld"
        make || echo "WARNING: HelloWorld example did not build. Continue setup, then troubleshoot Teknic separately."
    fi
fi

echo ""
echo "[6/6] Verifying install..."
echo -n "cmake: "; cmake --version | head -n 1
echo -n "g++: "; g++ --version | head -n 1
echo -n "make: "; make --version | head -n 1

echo ""
echo "Testing Python environment packages..."
conda run -n "$ENV_NAME" python - <<'PY'
import sys
print("Python:", sys.version.split()[0])
try:
    import PyQt6
    print("PyQt6: OK")
except Exception as exc:
    raise SystemExit(f"PyQt6 failed: {exc}")

try:
    import google.protobuf
    print("protobuf: OK")
except Exception as exc:
    raise SystemExit(f"protobuf failed: {exc}")
PY

echo ""
echo "======================================"
echo " Setup complete."
echo " IMPORTANT: reboot or log out/in so dialout group takes effect."
echo "======================================"
echo ""
echo "Next:"
echo "  conda activate $ENV_NAME"
echo "  cd TestStandGUI"
echo "  python initialization.py"
