#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_NAME="teststandgui"

if [ ! -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
    echo "ERROR: Miniforge/Conda was not found at:"
    echo "  $HOME/miniforge3/etc/profile.d/conda.sh"
    echo ""
    echo "Run ./setup.sh first."
    exit 1
fi

source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

cd "$PROJECT_ROOT/TestStandGUI"

python3 initialization.py
