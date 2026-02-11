#!/bin/bash
# VPN Management Script - OpenVPN with ProtonVPN
# Usage:
#   ./vpn.sh up [server]     - Connect (default: de-17, or specify de-188, de-263, etc.)
#   ./vpn.sh down            - Disconnect
#   ./vpn.sh status          - Show current status
#   ./vpn.sh switch [server] - Switch to different server
#   ./vpn.sh list            - List available configs
#   ./vpn.sh ip              - Show current public IP

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="/etc/openvpn/client"
CREDS_FILE="$CONFIG_DIR/proton-creds.txt"
PID_FILE="/var/run/openvpn-proton.pid"
LOG_FILE="$PROJECT_DIR/logs/vpn.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[VPN]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[VPN]${NC} $1"
}

error() {
    echo -e "${RED}[VPN]${NC} $1" >&2
}

get_public_ip() {
    curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown"
}

is_vpn_running() {
    pgrep -f "openvpn.*proton" > /dev/null 2>&1
}

get_vpn_ip() {
    ip addr show tun0 2>/dev/null | grep -oP 'inet \K[\d.]+' || echo "none"
}

cmd_status() {
    echo "=== VPN Status ==="
    if is_vpn_running; then
        log "OpenVPN: ${GREEN}RUNNING${NC}"
        log "Tunnel IP: $(get_vpn_ip)"
        log "Public IP: $(get_public_ip)"
    else
        warn "OpenVPN: ${RED}NOT RUNNING${NC}"
        log "Public IP: $(get_public_ip)"
    fi
    echo ""
    echo "Available configs:"
    cmd_list
}

cmd_list() {
    for conf in "$CONFIG_DIR"/proton-*.conf; do
        if [ -f "$conf" ] 2>/dev/null; then
            name=$(basename "$conf" .conf | sed 's/proton-//')
            echo "  - $name"
        fi
    done
    # Also check for the default
    if [ -f "$CONFIG_DIR/proton.conf" ]; then
        echo "  - default (de-17)"
    fi
}

cmd_up() {
    local server="${1:-default}"
    
    if is_vpn_running; then
        warn "VPN already running. Use 'vpn.sh switch $server' to change servers."
        return 1
    fi
    
    # Determine config file
    if [ "$server" = "default" ]; then
        config="$CONFIG_DIR/proton.conf"
    else
        config="$CONFIG_DIR/proton-$server.conf"
    fi
    
    if [ ! -f "$config" ]; then
        error "Config not found: $config"
        echo "Available configs:"
        cmd_list
        return 1
    fi
    
    log "Starting VPN with $server..."
    sudo openvpn --config "$config" --daemon --log "$LOG_FILE" --writepid "$PID_FILE"
    
    # Wait for connection - poll every 0.2s instead of 1s
    for i in {1..50}; do
        sleep 0.2
        if ip addr show tun0 &>/dev/null; then
            log "Connected!"
            log "Tunnel IP: $(get_vpn_ip)"
            log "Public IP: $(get_public_ip)"
            return 0
        fi
        echo -n "."
    done
    
    error "Failed to connect. Check $LOG_FILE"
    return 1
}

cmd_down() {
    if ! is_vpn_running; then
        warn "VPN not running"
        return 0
    fi
    
    log "Stopping VPN..."
    sudo pkill -f "openvpn.*proton" || true
    sleep 0.5
    
    if is_vpn_running; then
        warn "Force killing..."
        sudo pkill -9 -f "openvpn.*proton" || true
    fi
    
    log "VPN stopped"
    log "Public IP: $(get_public_ip)"
}

cmd_switch() {
    local server="${1:-}"
    
    if [ -z "$server" ]; then
        error "Usage: vpn.sh switch <server>"
        echo "Available configs:"
        cmd_list
        return 1
    fi
    
    log "Switching to $server..."
    cmd_down
    sleep 0.2
    cmd_up "$server"
}

cmd_rotate() {
    # ProtonVPN's de config load-balances across German servers
    # Just disconnect and reconnect to get a new IP
    log "Rotating VPN (reconnect to get new server)..."
    local old_ip=$(get_public_ip)
    cmd_down
    sleep 0.5
    cmd_up "de"  # Use de config which has all German servers
    local new_ip=$(get_public_ip)
    log "IP changed: $old_ip → $new_ip"
}

cmd_ip() {
    echo "$(get_public_ip)"
}

# Main
case "${1:-status}" in
    up)
        cmd_up "${2:-}"
        ;;
    down)
        cmd_down
        ;;
    status)
        cmd_status
        ;;
    switch)
        cmd_switch "${2:-}"
        ;;
    rotate)
        cmd_rotate
        ;;
    list)
        cmd_list
        ;;
    ip)
        cmd_ip
        ;;
    *)
        echo "Usage: $0 {up|down|status|switch|rotate|list|ip} [server]"
        echo ""
        echo "Commands:"
        echo "  up [server]     - Connect to VPN (default or specified server)"
        echo "  down            - Disconnect from VPN"
        echo "  status          - Show current VPN status"
        echo "  switch <server> - Switch to different server"
        echo "  rotate          - Reconnect to get new IP (same config, different server)"
        echo "  list            - List available server configs"
        echo "  ip              - Show current public IP"
        exit 1
        ;;
esac
