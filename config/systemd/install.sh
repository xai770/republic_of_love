#!/usr/bin/env bash
# Install systemd services for talent.yoga
# Run with: sudo bash config/systemd/install.sh
#
# Services:
#   talent-yoga     — FastAPI app (port 8000)
#   talent-yoga-bi  — Streamlit BI dashboard (port 8501)
#   (ollama.service is already installed separately)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing talent-yoga services..."

# Symlink service files
ln -sf "$SCRIPT_DIR/talent-yoga.service" /etc/systemd/system/talent-yoga.service
ln -sf "$SCRIPT_DIR/talent-yoga-bi.service" /etc/systemd/system/talent-yoga-bi.service

# Reload systemd
systemctl daemon-reload

# Enable (start on boot)
systemctl enable talent-yoga talent-yoga-bi

echo ""
echo "Services installed and enabled."
echo ""
echo "To start now (will take over from any running instances):"
echo "  sudo systemctl start talent-yoga"
echo "  sudo systemctl start talent-yoga-bi"
echo ""
echo "To check status:"
echo "  sudo systemctl status talent-yoga talent-yoga-bi"
echo ""
echo "After starting via systemd, you can remove these @reboot cron entries:"
echo "  @reboot /home/xai/Documents/ty_learn/scripts/start_bi.sh --daemon"
echo "  @reboot /home/xai/Documents/ty_learn/scripts/backfill_watchdog.sh"
