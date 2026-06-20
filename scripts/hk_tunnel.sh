#!/bin/bash
# HK SSH Tunnel — 自动重连保活
TUNNEL_PORT=18766
HK_HOST="43.129.75.222"
HK_PORT=8766
LOG="/var/log/hk-tunnel.log"

log() { echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"; }

while true; do
    # Check if tunnel is alive
    if ! curl -sf --max-time 5 "http://localhost:$TUNNEL_PORT/health" >/dev/null 2>&1; then
        log "Tunnel down, reconnecting..."
        pkill -f "ssh.*$TUNNEL_PORT:localhost:$HK_PORT" 2>/dev/null
        sleep 2
        ssh -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -N -L "$TUNNEL_PORT:localhost:$HK_PORT" \
            "ubuntu@$HK_HOST" >> "$LOG" 2>&1 &
        log "SSH PID: $!"
    fi
    sleep 30
done
