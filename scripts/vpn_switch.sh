#!/bin/bash
# ==============================================================================
# VPN Switch - Safe WireGuard rotation using wg-quick only
# ==============================================================================
# Usage:
#   ./vpn_switch.sh up de-17      # Connect to DE-17
#   ./vpn_switch.sh down          # Disconnect all
#   ./vpn_switch.sh status        # Show current state
#   ./vpn_switch.sh list          # List available configs
#   ./vpn_switch.sh panic         # Emergency reset
#
# IMPORTANT: This script uses wg-quick ONLY. Do not mix with NetworkManager.
# ==============================================================================

set -e

CONFIG_DIR="/etc/wireguard"
PROJECT_CONFIG_DIR="/home/xai/Documents/ty_learn/config"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ==============================================================================
# Get all active WireGuard interfaces
# ==============================================================================
get_active_wg_interfaces() {
    ip link show 2>/dev/null | grep -oP 'wg[^:@]+' | sort -u || true
}

# ==============================================================================
# Bring down ALL WireGuard interfaces (nuclear option)
# ==============================================================================
down_all_wg() {
    local interfaces=$(get_active_wg_interfaces)
    
    if [ -z "$interfaces" ]; then
        log_info "No WireGuard interfaces active"
        return 0
    fi
    
    for iface in $interfaces; do
        log_info "Bringing down $iface..."
        
        # Try wg-quick first (proper cleanup)
        if sudo wg-quick down "$iface" 2>/dev/null; then
            log_info "  ✓ $iface down via wg-quick"
        else
            # Fallback: force delete the interface
            log_warn "  wg-quick failed, force-deleting interface..."
            sudo ip link delete "$iface" 2>/dev/null || true
        fi
    done
    
    # Verify all gone
    local remaining=$(get_active_wg_interfaces)
    if [ -n "$remaining" ]; then
        log_error "Failed to remove: $remaining"
        return 1
    fi
    
    log_info "All WireGuard interfaces down"
}

# ==============================================================================
# Bring up a specific WireGuard config
# ==============================================================================
up_wg() {
    local config_name="$1"
    
    if [ -z "$config_name" ]; then
        log_error "Usage: vpn_switch.sh up <config-name>"
        log_info "  Example: vpn_switch.sh up de-17"
        list_configs
        return 1
    fi
    
    # Normalize config name (accept "de-17", "DE-17", "wg-DE-17", etc.)
    local normalized=$(echo "$config_name" | tr '[:lower:]' '[:upper:]' | sed 's/^WG-//')
    local config_file="$CONFIG_DIR/wg-$normalized.conf"
    
    # Check if config exists in /etc/wireguard
    if [ ! -f "$config_file" ]; then
        # Try to find in project config dir and copy
        local project_file="$PROJECT_CONFIG_DIR/wg-$normalized.conf"
        if [ -f "$project_file" ]; then
            log_info "Copying config from project dir..."
            sudo cp "$project_file" "$config_file"
            sudo chmod 600 "$config_file"
        else
            log_error "Config not found: $config_file"
            log_info "Available configs:"
            list_configs
            return 1
        fi
    fi
    
    # CRITICAL: Bring down any existing WG first
    log_info "Ensuring no other WG interfaces are active..."
    down_all_wg
    
    # Bring up the requested config
    local iface_name="wg-$normalized"
    log_info "Bringing up $iface_name..."
    
    if ! sudo wg-quick up "$iface_name" 2>&1; then
        log_error "Failed to bring up $iface_name"
        return 1
    fi
    
    # Verify it's up
    sleep 1
    if ! ip link show "$iface_name" &>/dev/null; then
        log_error "Interface $iface_name not found after wg-quick up"
        return 1
    fi
    
    # Test connectivity
    log_info "Testing connectivity..."
    if ping -c 1 -W 5 1.1.1.1 &>/dev/null; then
        log_info "✓ IP connectivity OK"
    else
        log_error "✗ IP connectivity FAILED"
        log_warn "Bringing VPN down..."
        down_all_wg
        return 1
    fi
    
    if ping -c 1 -W 5 google.com &>/dev/null; then
        log_info "✓ DNS resolution OK"
    else
        log_warn "✗ DNS resolution FAILED (IP works, DNS doesn't)"
    fi
    
    # Show status
    echo ""
    sudo wg show "$iface_name" | head -10
    echo ""
    log_info "VPN $iface_name is UP"
}

# ==============================================================================
# Show status
# ==============================================================================
show_status() {
    echo "=== WireGuard Status ==="
    
    local interfaces=$(get_active_wg_interfaces)
    
    if [ -z "$interfaces" ]; then
        echo "No WireGuard interfaces active"
        echo ""
        echo "Available configs:"
        list_configs
        return 0
    fi
    
    for iface in $interfaces; do
        echo ""
        echo "Interface: $iface"
        sudo wg show "$iface" 2>/dev/null || echo "  (unable to query)"
    done
    
    echo ""
    echo "=== Connectivity ==="
    ping -c 1 -W 3 1.1.1.1 &>/dev/null && echo "IP:  ✓ OK" || echo "IP:  ✗ FAILED"
    ping -c 1 -W 3 google.com &>/dev/null && echo "DNS: ✓ OK" || echo "DNS: ✗ FAILED"
}

# ==============================================================================
# List available configs
# ==============================================================================
list_configs() {
    echo ""
    echo "=== Available in /etc/wireguard ==="
    ls -1 "$CONFIG_DIR"/*.conf 2>/dev/null | xargs -I{} basename {} .conf | sed 's/^/  /' || echo "  (none)"
    
    echo ""
    echo "=== Available in project config ==="
    ls -1 "$PROJECT_CONFIG_DIR"/wg-DE-*.conf 2>/dev/null | xargs -I{} basename {} .conf | sed 's/^/  /' || echo "  (none)"
}

# ==============================================================================
# Panic - emergency reset
# ==============================================================================
panic() {
    log_warn "🚨 PANIC MODE - Emergency network reset"
    
    # Kill all WG interfaces
    down_all_wg
    
    # Kill any NetworkManager WG connections too
    for conn in $(nmcli -t -f NAME c show 2>/dev/null | grep '^wg-'); do
        log_info "Downing NM connection $conn..."
        nmcli c down "$conn" 2>/dev/null || true
    done
    
    # Force-delete any remaining wg interfaces
    for iface in $(ip link show 2>/dev/null | grep -oP 'wg[^:@]+'); do
        log_info "Force-deleting $iface..."
        sudo ip link delete "$iface" 2>/dev/null || true
    done
    
    # Reset DNS to router
    log_info "Resetting DNS to router..."
    echo "nameserver 192.168.0.1" | sudo tee /etc/resolv.conf > /dev/null
    
    # Restart NetworkManager
    log_info "Restarting NetworkManager..."
    sudo systemctl restart NetworkManager
    
    sleep 2
    
    # Verify
    echo ""
    show_status
}

# ==============================================================================
# Main
# ==============================================================================
case "${1:-status}" in
    up)
        up_wg "$2"
        ;;
    down)
        down_all_wg
        ;;
    status)
        show_status
        ;;
    list)
        list_configs
        ;;
    panic)
        panic
        ;;
    *)
        echo "Usage: $0 {up <config>|down|status|list|panic}"
        echo ""
        echo "Commands:"
        echo "  up <config>  - Connect to VPN (e.g., 'up de-17')"
        echo "  down         - Disconnect all VPNs"
        echo "  status       - Show current state"
        echo "  list         - List available configs"
        echo "  panic        - Emergency reset (kills everything)"
        exit 1
        ;;
esac
