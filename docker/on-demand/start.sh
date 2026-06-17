#!/bin/bash
set -e

export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p "$XDG_RUNTIME_DIR"

# Start virtual framebuffer
Xvfb ${DISPLAY} -screen 0 ${RESOLUTION} -ac +extension GLX &
sleep 1

# Start lightweight window manager
fluxbox &
sleep 1

# Start VNC server (no password for internal use; add -passwd for auth)
x11vnc -display ${DISPLAY} -forever -shared -nopw -rfbport ${VNC_PORT} &
sleep 1

# Start noVNC websocket proxy
websockify --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT} &

# Start status server (used by lobby to show session availability)
python /status_server.py &

# Set noVNC defaults: auto-connect, local scaling, no prompt
NOVNC_URL="http://localhost:${NOVNC_PORT}/vnc.html?resize=scale&autoconnect=true"
echo "============================================"
echo " Badger GUI available at:"
echo "   ${NOVNC_URL}"
echo "============================================"

# Idle timeout monitor: exit container if no VNC client connected for IDLE_TIMEOUT seconds
if [ -n "${IDLE_TIMEOUT}" ] && [ "${IDLE_TIMEOUT}" -gt 0 ] 2>/dev/null; then
    (
        idle_count=0
        while true; do
            sleep 30
            # Check if any VNC clients are connected
            clients=$(x11vnc -query clients 2>/dev/null | grep -c "^client:" || echo "0")
            if [ "$clients" -eq 0 ]; then
                idle_count=$((idle_count + 30))
                if [ "$idle_count" -ge "${IDLE_TIMEOUT}" ]; then
                    echo "No VNC clients for ${IDLE_TIMEOUT}s, shutting down..."
                    kill 1
                    exit 0
                fi
            else
                idle_count=0
            fi
        done
    ) &
fi

# Launch Badger GUI in background, then maximize the window
badger -g &
BADGER_PID=$!

# Wait for the window to appear, then maximize it
sleep 3
xdotool search --name "Badger" windowactivate --sync windowsize 100% 100% windowmove 0 0 2>/dev/null || true

# Keep container alive as long as badger runs
wait $BADGER_PID || true

# Restart loop if badger exits
while true; do
    echo "Badger exited, restarting in 2s..."
    sleep 2
    badger -g &
    BADGER_PID=$!
    sleep 3
    xdotool search --name "Badger" windowactivate --sync windowsize 100% 100% windowmove 0 0 2>/dev/null || true
    wait $BADGER_PID || true
done
