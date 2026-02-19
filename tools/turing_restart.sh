#!/usr/bin/env bash
# Restart the talent.yoga FastAPI server via systemd
# Usage: sudo bash tools/turing_restart.sh
#
# Since Feb 19 2026 the app runs as systemd service talent-yoga.
# This script wraps the restart/status cycle.

set -e

if [[ $EUID -ne 0 ]]; then
    echo "⚠  This script needs sudo. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

echo "⏹  Restarting talent-yoga..."
systemctl restart talent-yoga
sleep 2

if systemctl is-active --quiet talent-yoga; then
    echo "✅ talent-yoga is active ($(systemctl show -p MainPID --value talent-yoga))"
else
    echo "❌ talent-yoga failed to start:"
    systemctl status talent-yoga --no-pager
    exit 1
fi
