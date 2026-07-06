FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV RESOLUTION=1920x1080x24
ENV IDLE_TIMEOUT=600

# Confine EPICS Channel Access to pod-localhost: the lume-pva model server (CA)
# and Badger's pyepics client (CA) only talk to each other, never across pods.
ENV EPICS_CA_ADDR_LIST=127.0.0.1
ENV EPICS_CA_AUTO_ADDR_LIST=NO
ENV EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
ENV EPICS_CAS_BEACON_ADDR_LIST=127.0.0.1

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

# Maximize only the main Badger window; let dialogs/popups open at native size
RUN mkdir -p /root/.fluxbox && \
    echo "[app] (title=Badger mini.*)\n  [Maximized] {yes}\n[end]" > /root/.fluxbox/apps

# Install CPU-only PyTorch first, before anything that depends on torch (badger,
# xopt/botorch, lume-torch). This avoids pulling the multi-GB CUDA wheels.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Badger and dependencies
COPY . /app
WORKDIR /app
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
RUN pip install --no-cache-dir -e ".[dev]"

# Install latest xopt from main branch
RUN pip install --no-cache-dir git+https://github.com/xopt-org/Xopt.git@main

# Install the LCLS FEL surrogate model (wrapped by fel_runner.py; provides the
# trained model weights as package data)
RUN pip install --no-cache-dir git+https://github.com/slaclab/LCLS_FEL_Surrogate.git@main

# Install the lume-pva serving stack (not on PyPI; install from git in dependency
# order). fel_runner.py uses these to serve the FEL model as EPICS PVs (CA + PVA)
# so Badger talks to it through the epics interface instead of running it in-process.
# Pin to the commits from the known-good fel-lume-pva env. lume-pva main has since
# moved past e1f8335 to a version that calls model.get() on input vars at startup
# (before any set()), which the FEL surrogate rejects with a KeyError.
RUN pip install --no-cache-dir \
    git+https://github.com/slaclab/lume-base \
    git+https://github.com/lume-science/lume-torch.git \
    git+https://github.com/slac-epics/pvua \
    git+https://github.com/lume-science/lume-pva.git@e1f8335036785fe319003eeffd8195eedfe99f23

# FEL surrogate model server (serves the model as EPICS PVs; launched by start.sh
# before Badger)
COPY docker/fel_runner.py /fel_runner.py

# Environment/interface plugins + routine templates come from the external
# Badger-Plugins repo (the fork, for now). setup_badger.py points the plugin and
# template roots here.
ENV BADGER_PLUGINS_DIR=/opt/Badger-Plugins
RUN git clone --depth 1 https://github.com/pluflou/Badger-Plugins.git "$BADGER_PLUGINS_DIR"

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
