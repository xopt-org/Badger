# Badger GUI On-Demand (noVNC)

Run the Badger GUI in a container accessible via web browser — no local install needed.

## Architecture

```
Browser → Ingress (/badger) → Gateway (nginx)
                                ├── /badger/              → lobby page (session picker)
                                ├── /badger/session/0/    → badger-gui-0 pod
                                ├── /badger/session/1/    → badger-gui-1 pod
                                └── /badger/session/N/    → badger-gui-N pod
```

Each pod runs: `Xvfb → fluxbox → x11vnc → websockify/noVNC → Badger GUI + status server`

## Production URL

```
https://ard-modeling-service.slac.stanford.edu/badger/
```

## Quick Start (Local)

Single instance (no gateway, direct access):

```bash
# From the repository root:
docker build --platform linux/amd64 -f docker/on-demand/Dockerfile -t badger-novnc .
docker run --rm -p 6080:6080 badger-novnc

# Open: http://localhost:6080/vnc.html?resize=scale&autoconnect=true
```

Multi-session local test (with gateway + lobby):

```bash
cd docker/on-demand
docker compose up --build

# Lobby at: http://localhost:6080/badger/
```

## Kubernetes Deployment

### Initial Setup

```bash
# 1. Build and push both images (must be linux/amd64)
docker build --platform linux/amd64 -f docker/on-demand/Dockerfile -t pluflou/badger-novnc:latest .
docker build --platform linux/amd64 -f docker/on-demand/gateway/Dockerfile docker/on-demand/gateway/ -t pluflou/badger-gateway:latest
docker push pluflou/badger-novnc:latest
docker push pluflou/badger-gateway:latest

# 2. Deploy everything (order matters)
kubectl apply -f docker/on-demand/k8s/namespace.yaml
kubectl apply -f docker/on-demand/k8s/statefulset.yaml
kubectl apply -f docker/on-demand/k8s/service.yaml
kubectl apply -f docker/on-demand/k8s/gateway.yaml
kubectl apply -f docker/on-demand/k8s/daily-restart-cronjob.yaml

# 3. Watch pods come up
kubectl get pods -n badger-gui -w
# Expected: badger-gui-0 through badger-gui-19 + badger-gateway-xxxxx
```

### Updating After Code Changes

```bash
# Rebuild and push the updated image
docker build --platform linux/amd64 -f docker/on-demand/Dockerfile -t pluflou/badger-novnc:latest .
docker push pluflou/badger-novnc:latest

# Rolling restart of all session pods
kubectl rollout restart statefulset badger-gui -n badger-gui
```

### Updating the Gateway (lobby page or nginx config)

```bash
docker build --platform linux/amd64 -f docker/on-demand/gateway/Dockerfile docker/on-demand/gateway/ -t pluflou/badger-gateway:latest
docker push pluflou/badger-gateway:latest
kubectl rollout restart deployment badger-gateway -n badger-gui
```

## Multi-User Model

- **StatefulSet** creates 20 pods with stable names (`badger-gui-0` through `badger-gui-19`)
- **Headless Service** gives each pod a DNS name for the gateway to route to
- **Gateway** (nginx) serves a lobby page and routes `/badger/session/N/` to the correct pod
- **Status endpoint** (port 8080) on each pod reports VNC client count so the lobby shows occupied/available

Users pick an available session from the lobby. Each session is fully isolated — no shared state between users.

### What Happens When a User Closes Their Browser Tab

1. The Badger session **keeps running** inside the pod (no data lost)
2. If the user reconnects within `IDLE_TIMEOUT` seconds, they pick up where they left off
3. After `IDLE_TIMEOUT` (default 10 min) with no VNC clients, the pod self-terminates
4. Kubernetes automatically restarts it as a fresh session

### Nightly Reset

Runs are archived to each pod's ephemeral filesystem (no PersistentVolume), so they
survive until the pod's container restarts. A pod that stays connected (e.g. a browser
tab left open) never hits the idle timeout, so its archived runs would otherwise leak
across users and days. `daily-restart-cronjob.yaml` runs `kubectl rollout restart
statefulset/badger-gui` at **midnight Pacific** (`America/Los_Angeles`, DST-aware) to
guarantee every session starts the day fresh. It uses a dedicated `badger-restarter`
ServiceAccount with a Role scoped to patching the StatefulSet.

### Scaling

```bash
# Add more sessions
kubectl scale statefulset badger-gui -n badger-gui --replicas=30
```

**Important:** Also update `TOTAL_SESSIONS` in `gateway/lobby.html` to match, then rebuild and push the gateway image.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `RESOLUTION` | `1920x1080x24` | Virtual display resolution |
| `VNC_PORT` | `5900` | Internal VNC port |
| `NOVNC_PORT` | `6080` | noVNC web port |
| `IDLE_TIMEOUT` | `600` | Seconds before idle pod self-terminates (0 = disabled) |

## Performance Tuning

PyTorch autodetects the wrong thread count inside containers. `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, and `OPENBLAS_NUM_THREADS` are set explicitly in the StatefulSet env to match the CPU limit.

## EPICS Access

To connect to EPICS IOCs, add to the StatefulSet env in `k8s/statefulset.yaml`:

```yaml
env:
  - name: EPICS_CA_ADDR_LIST
    value: "your-ioc-gateway.slac.stanford.edu"
  - name: EPICS_CA_AUTO_ADDR_LIST
    value: "NO"
```

Then reapply: `kubectl apply -f docker/on-demand/k8s/statefulset.yaml`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ErrImagePull` on gateway pod | Image not pushed or wrong platform | `docker build --platform linux/amd64 ...` then `docker push` |
| `ErrImagePull` on badger pods | Image not pushed | `docker push pluflou/badger-novnc:latest` |
| Lobby shows all sessions "Offline" | Pods not ready yet or DNS not resolving | `kubectl get pods -n badger-gui` — wait for Running state |
| Lobby shows "In Use" but session is free | Status server stale after reconnect | Will self-correct within 5s (poll interval) |
| 502 error on session click | Target pod not ready | Wait ~30s for pod startup, check with `kubectl logs badger-gui-N -n badger-gui` |
| "Failed to connect to server" in noVNC | WebSocket blocked by ingress | Ensure no `configuration-snippet` annotation on ingress; `proxy-http-version: "1.1"` is sufficient |
| Shared session between users | Old deployment still running | Delete old: `kubectl delete deployment badger-gui -n badger-gui` |
| Browser cache issues (400 error) | Stale HSTS/redirect cache | Clear site data or use incognito |
| Readiness probe failing on gateway | Probe path doesn't match prefix | Probe must use `/badger/` not `/` |

## Ingress Notes

The ingress requires only these annotations for full websocket support:

```yaml
nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
```

Do **not** add `configuration-snippet` with `proxy_set_header Upgrade/Connection` — the nginx ingress controller handles websocket upgrades natively with `proxy-http-version: "1.1"` and adding explicit headers can break the handshake.

## Security Notes

- VNC server runs with **no password** (intended for internal use behind ingress IP whitelist)
- Ingress restricts access to SLAC network ranges only
- For additional auth, add an OAuth proxy sidecar to the gateway deployment

## File Structure

```
docker/on-demand/
├── Dockerfile              # Badger + Xvfb + VNC + noVNC image
├── start.sh                # Container entrypoint (starts all services)
├── setup_badger.py         # Pre-configures Badger for headless use
├── status_server.py        # HTTP endpoint reporting VNC client count
├── docker-compose.yml      # Local multi-session testing
├── gateway/
│   ├── Dockerfile          # nginx gateway image
│   ├── nginx.conf          # K8s nginx config (uses pod DNS)
│   ├── nginx.local.conf    # Local docker-compose nginx config
│   └── lobby.html          # Session picker UI
└── k8s/
    ├── namespace.yaml      # badger-gui namespace
    ├── statefulset.yaml    # 20 Badger session pods
    ├── service.yaml        # Headless service + ingress
    ├── gateway.yaml        # Gateway deployment + service
    └── daily-restart-cronjob.yaml  # Nightly statefulset restart (clears runs)
```
