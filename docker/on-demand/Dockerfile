FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV RESOLUTION=1920x1080x24
ENV IDLE_TIMEOUT=600

# System dependencies for Xvfb, VNC, window manager, and PyQt5
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    xauth \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    libgl1 \
    libglib2.0-0 \
    libfontconfig1 \
    libxkbcommon0 \
    libdbus-1-3 \
    libegl1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-keysyms1 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    git \
    procps \
    iproute2 \
    xdotool \
    && rm -rf /var/lib/apt/lists/*

# Configure fluxbox to maximize all windows by default
RUN mkdir -p /root/.fluxbox && \
    echo "[app] (name=.*)\n  [Maximized] {yes}\n[end]" > /root/.fluxbox/apps

# Install Badger and dependencies
COPY . /app
WORKDIR /app
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
RUN pip install --no-cache-dir -e ".[dev]"

# Install latest xopt from main branch
RUN pip install --no-cache-dir git+https://github.com/xopt-org/Xopt.git@main

# Pre-configure Badger so it doesn't prompt on first launch
RUN mkdir -p /root/.config && python docker/on-demand/setup_badger.py

# Status server for lobby health checks
COPY docker/on-demand/status_server.py /status_server.py

# Startup script
COPY docker/on-demand/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE ${NOVNC_PORT}
EXPOSE 8080

CMD ["/start.sh"]
