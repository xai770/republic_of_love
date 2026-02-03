#!/bin/bash
# Cloudflare Tunnel Setup for talent.yoga
# 
# Prerequisites: 
#   - cloudflared installed (done!)
#   - Cloudflare account with talent.yoga domain
#
# One-time setup (run interactively):
#   1. cloudflared tunnel login
#      (Opens browser - authenticate with Cloudflare)
#   
#   2. cloudflared tunnel create talent-yoga
#      (Creates tunnel, outputs tunnel UUID)
#   
#   3. Create config file: ~/.cloudflared/config.yml
#      tunnel: <TUNNEL_UUID>
#      credentials-file: /home/xai/.cloudflared/<TUNNEL_UUID>.json
#      ingress:
#        - hostname: talent.yoga
#          service: http://localhost:8000
#        - hostname: www.talent.yoga
#          service: http://localhost:8000
#        - service: http_status:404
#   
#   4. cloudflared tunnel route dns talent-yoga talent.yoga
#   5. cloudflared tunnel route dns talent-yoga www.talent.yoga
#
# Run tunnel (foreground for testing):
#   cloudflared tunnel run talent-yoga
#
# Install as systemd service (recommended for production):
#   sudo cloudflared service install
#   sudo systemctl enable cloudflared
#   sudo systemctl start cloudflared
#
# Check status:
#   cloudflared tunnel info talent-yoga
#   sudo systemctl status cloudflared

set -e

echo "=== Cloudflare Tunnel Quick Start ==="
echo ""
echo "Step 1: Login to Cloudflare (browser will open)"
echo "  cloudflared tunnel login"
echo ""
echo "Step 2: Create tunnel"
echo "  cloudflared tunnel create talent-yoga"
echo ""
echo "Step 3: Run quick tunnel (for testing):"
echo "  cloudflared tunnel --url http://localhost:8000"
echo ""
echo "For persistent tunnel, create config and install as service."
echo "See comments in this script for details."
