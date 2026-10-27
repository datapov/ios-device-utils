#!/bin/zsh
# Double-click launcher for macOS
cd "$(dirname "$0")"
if ! command -v idevice_id >/dev/null 2>&1; then
  echo "libimobiledevice not found."
  echo "Install it first in Terminal:"
  echo "  brew install libimobiledevice"
  echo ""
  read -k 1 "?Press any key to close..."
  exit 1
fi
python3 battery_health.py --gui
