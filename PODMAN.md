# Podman Compose Setup

Running Fleet Status Dashboard with Podman (rootless or privileged).

## Prerequisites

```bash
# Install podman
# macOS (via Homebrew)
brew install podman

# Fedora/RHEL
sudo dnf install podman podman-compose

# Ubuntu/Debian
sudo apt-get install podman podman-compose

# Verify installation
podman --version
podman-compose --version
```

## Quick Start

### Option 1: Rootless (Recommended)

```bash
# Initialize podman machine (macOS/Windows)
podman machine init
podman machine start

# Clone and run
git clone https://github.com/fmendonca/fleet-status.git
cd fleet-status

# Start containers
podman-compose up

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

### Option 2: Privileged (Linux)

```bash
sudo podman-compose up
```

## Common Commands

```bash
# Build images
podman-compose build

# Start containers
podman-compose up
podman-compose up -d  # Background

# Stop containers
podman-compose down

# View logs
podman-compose logs -f backend
podman-compose logs -f frontend

# Execute commands in container
podman-compose exec backend python -m pytest

# Remove volumes (clean reset)
podman-compose down -v
```

## Network Setup

Containers use bridge network `fleet-net`:
- Backend: `http://backend:8000` (internal)
- Frontend: `http://localhost:3000` (external)
- API calls: Frontend → Backend via bridge

## Podman Rootless Networking

If running rootless, ports may need special handling:

```bash
# Check listening ports
podman ps

# If port forwarding not working:
# 1. Check podman machine is running: podman machine ls
# 2. Expose ports in compose: ports: ["8000:8000"]
# 3. Or use podman machine ssh to access
```

## Building Images for OpenShift

```bash
# Build with rootless podman
podman build -t fleet-status-backend ./backend
podman build -t fleet-status-frontend ./frontend

# Tag for registry
podman tag fleet-status-backend quay.io/your-user/fleet-status-backend:v1.0
podman tag fleet-status-frontend quay.io/your-user/fleet-status-frontend:v1.0

# Push to registry
podman push quay.io/your-user/fleet-status-backend:v1.0
podman push quay.io/your-user/fleet-status-frontend:v1.0

# Verify
podman images | grep fleet-status
```

## Troubleshooting

### Containers won't start
```bash
# Check podman daemon
podman ps

# If rootless and machine stopped:
podman machine start

# Check logs
podman-compose logs
```

### Port conflicts (8000/3000 already in use)
```bash
# Change ports in docker-compose.yml
# Or kill existing containers:
podman kill fleet-status-backend fleet-status-frontend
podman rm fleet-status-backend fleet-status-frontend
```

### Network issues between containers
```bash
# Inspect network
podman network inspect fleet-net

# Recreate network
podman-compose down -v
podman-compose up
```

### Permission denied (Linux)
```bash
# Use sudo
sudo podman-compose up

# Or add user to podman group
sudo usermod -aG podman $USER
newgrp podman  # Reload group membership
```

## Environment Variables

```bash
# Mock mode (no real Thanos)
export MOCK_MODE=true

# Real Thanos URL
export THANOS_URL=https://your-thanos-url
export THANOS_TOKEN=your-bearer-token

# Then start
podman-compose up
```

## Development Workflow

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export MOCK_MODE=true
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Or use podman-compose for both
podman-compose up
```

## Production Notes

- Rootless podman runs as non-root (more secure)
- Use `podman-compose` for orchestration (not pod files)
- Tag images before pushing to registry
- Verify images before deploying to OpenShift

## Comparison: Docker vs Podman

| Feature | Docker | Podman |
|---------|--------|--------|
| Rootless | ⚠️ Beta | ✅ Default |
| Daemon | ✅ Required | ✅ Systemd socket |
| Compose | ✅ docker-compose | ✅ podman-compose |
| Pods | ❌ N/A | ✅ Native support |
| OCI | ✅ Yes | ✅ Yes |
| Performance | ⚠️ Daemon overhead | ✅ Direct |

## References

- https://podman.io/
- https://github.com/containers/podman-compose
- https://docs.podman.io/en/latest/
