#!/usr/bin/env bash
# Install all systemd services for talent.yoga
# Run with: sudo bash config/systemd/install.sh
#
# Services:
#   talent-yoga          — FastAPI app (port 8000)
#   talent-yoga-bi       — Streamlit BI dashboard (port 8501)
#   talent-yoga-backup   — Daily backup (timer-triggered at 02:00)
#   (ollama.service is already installed separately)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing talent-yoga services..."

# Symlink service files
ln -sf "$SCRIPT_DIR/talent-yoga.service" /etc/systemd/system/talent-yoga.service
ln -sf "$SCRIPT_DIR/talent-yoga-bi.service" /etc/systemd/system/talent-yoga-bi.service
ln -sf "$SCRIPT_DIR/talent-yoga-backup.service" /etc/systemd/system/talent-yoga-backup.service
ln -sf "$SCRIPT_DIR/talent-yoga-backup.timer" /etc/systemd/system/talent-yoga-backup.timer

# Reload systemd
systemctl daemon-reload

# Enable (start on boot)
systemctl enable talent-yoga talent-yoga-bi talent-yoga-backup.timer

echo ""
echo "Services installed and enabled:"
echo "  talent-yoga           — FastAPI (port 8000)"
echo "  talent-yoga-bi        — Streamlit BI (port 8501)"
echo "  talent-yoga-backup    — Daily backup (02:00, timer)"
echo ""
echo "To start now (will take over from any running instances):"
echo "  sudo systemctl start talent-yoga"
echo "  sudo systemctl start talent-yoga-bi"
echo "  sudo systemctl start talent-yoga-backup.timer"
echo ""
echo "To check status:"
echo "  systemctl status talent-yoga talent-yoga-bi"
echo "  systemctl list-timers talent-yoga-backup.timer"
echo ""
echo "After starting via systemd, remove these @reboot cron entries:"
echo "  @reboot .../start_bi.sh --daemon"
echo "  @reboot .../backfill_watchdog.sh"
echo ""
echo "And remove these backup/maintenance cron entries (now in backup_all.sh):"
echo "  0 2 * * * .../usb_backup.sh"
echo "  0 3 * * 0 .../usb_backup.sh --full"
echo "  0 3 * * * .../backup_turing.sh"
echo "  5 3 * * * .../export_schema.sh"
echo "  0 3 * * * .../rotate_logs.sh"
echo "  0 4 * * * /usr/sbin/logrotate ..."
echo "  0 3 * * * .../nightly_invalidate_stale.py"
