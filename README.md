# OpenShift Multi-Cluster Fleet Status Dashboard

Real-time monitoring dashboard for managing multiple Red Hat OpenShift clusters via RHACM.

## Architecture

The dashboard aggregates metrics from all OpenShift clusters managed by RHACM through Thanos (RHACM Observability):

```
Managed Clusters → RHACM Hub → Thanos/rbac-query-proxy → Backend → Frontend
```

Key principles:
- **Single pane of glass**: View all clusters from one dashboard
- **Centralized metrics**: All data flows through Thanos (no individual cluster API calls)
- **No client-side tokens**: Authentication is backend-only
- **Resilient**: Graceful degradation if metrics unavailable

## Prerequisites

- Red Hat OpenShift 4.10+
- RHACM 2.5+ with Observability enabled
- Python 3.12+
- Node.js 18+
- kubectl/oc CLI access

## Finding Thanos URL

Discover the rbac-query-proxy route in the Hub cluster:

```bash
oc get route rbac-query-proxy \
  -n open-cluster-management-observability \
  -o jsonpath='https://{.spec.host}'
```

Get authentication token:

```bash
oc whoami -t
```

## Getting Started (Development)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

Set environment variables:

```bash
export THANOS_URL="https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local"
export THANOS_TOKEN="<your-token>"
export THANOS_TLS_VERIFY=false  # Only for dev without proper certs
export MOCK_MODE=false
```

Run backend:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

Frontend runs on `http://localhost:3000`

## API Endpoints

### Fleet Metrics
```
GET /api/v1/fleet
```

Returns overall fleet status with cluster, node, CPU, memory, and alert counts.

### Clusters
```
GET /api/v1/clusters
GET /api/v1/clusters/{cluster_id}
GET /api/v1/clusters/{cluster_id}/nodes
```

### Alerts
```
GET /api/v1/alerts
```

### Health & Diagnostics
```
GET /api/v1/health
GET /healthz
GET /readyz
```

### Prometheus Metrics
```
GET /metrics
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `THANOS_URL` | `http://localhost:9090` | Thanos/rbac-query-proxy URL |
| `THANOS_TOKEN` | - | Bearer token for Thanos auth |
| `THANOS_TLS_VERIFY` | `true` | Verify TLS certificates |
| `THANOS_CA_FILE` | - | Path to CA certificate file |
| `CACHE_TTL` | `30` | Cache lifetime in seconds |
| `CPU_WARNING` | `70` | CPU warning threshold (%) |
| `CPU_HIGH` | `85` | CPU high threshold (%) |
| `CPU_CRITICAL` | `90` | CPU critical threshold (%) |
| `MEMORY_WARNING` | `75` | Memory warning threshold (%) |
| `ALERT_IGNORE_LIST` | `Watchdog,InfoInhibitor` | Comma-separated alert names to ignore |
| `MOCK_MODE` | `false` | Enable mock data (development only) |

## PromQL Queries Used

### Cluster Discovery
```promql
acm_managed_cluster_info
```

### Node Metrics
```promql
count by (cluster) (kube_node_info)
kube_node_status_condition{condition="Ready", status="true"}
kube_node_spec_unschedulable
```

### CPU Utilization
```promql
100 - (avg by (cluster, instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

### Memory Utilization
```promql
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

### Alerts
```promql
ALERTS{alertstate="firing"}
```

## Cluster Health Status

**HEALTHY**: All nodes ready, no critical/warning alerts, CPU/memory within thresholds
**WARNING**: Some metrics above warning threshold or non-critical alerts
**CRITICAL**: NotReady nodes, critical alerts, or critical thresholds exceeded
**NO_DATA**: Cluster known to RHACM but no recent metrics

## Deployment to OpenShift

### 1. Build container images

Backend:
```bash
cd backend
podman build -t quay.io/YOUR_REGISTRY/fleet-status-backend:latest .
podman push quay.io/YOUR_REGISTRY/fleet-status-backend:latest
```

Frontend:
```bash
cd frontend
podman build -t quay.io/YOUR_REGISTRY/fleet-status-frontend:latest .
podman push quay.io/YOUR_REGISTRY/fleet-status-frontend:latest
```

### 2. Configure secrets

Edit `openshift/secret.yaml` with your Thanos credentials:

```bash
oc create secret generic fleet-status-backend-secret \
  --from-literal=THANOS_URL=<thanos-url> \
  --from-literal=THANOS_TOKEN=<token> \
  -n fleet-status --dry-run=client -o yaml | oc apply -f -
```

### 3. Deploy

```bash
# Create namespace
oc apply -f openshift/namespace.yaml

# Deploy ConfigMap and Secret
oc apply -f openshift/configmap.yaml
oc apply -f openshift/secret.yaml

# Deploy RBAC
oc apply -f openshift/rbac.yaml

# Deploy backend and frontend
oc apply -f openshift/backend-deployment.yaml
oc apply -f openshift/frontend-deployment.yaml
```

### 4. Access dashboard

Get the route:

```bash
oc get route fleet-status -n fleet-status -o jsonpath='{.spec.host}'
```

Access via: `https://<route-host>`

## Troubleshooting

### Check backend logs

```bash
oc logs -f deployment/fleet-status-backend -n fleet-status
```

### Test Thanos connectivity

```bash
BACKEND_POD=$(oc get pods -n fleet-status -l component=backend -o jsonpath='{.items[0].metadata.name}')
oc exec -it $BACKEND_POD -n fleet-status -- curl -k \
  -H "Authorization: Bearer $THANOS_TOKEN" \
  https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local/api/v1/query?query=up
```

### Check discovered metrics

Visit: `https://<route>/api/v1/health`

Should show:
- `thanos_connected: true`
- Available metrics list
- `cluster_label` and `node_label` detected

### Enable debug logging

```bash
oc set env deployment/fleet-status-backend \
  -n fleet-status \
  LOG_LEVEL=DEBUG
```

## Validation

Verify deployment with checklist:

```bash
# 1. Compare cluster counts
RHACM_CLUSTERS=$(oc get managedclusters | wc -l)
DASHBOARD_CLUSTERS=$(curl -s https://fleet-status-route/api/v1/fleet | jq .clusters.total)
[ "$RHACM_CLUSTERS" = "$DASHBOARD_CLUSTERS" ] && echo "✓ Cluster count OK" || echo "✗ Mismatch"

# 2. Check node count per cluster
oc get nodes -L cluster.open-cluster-management.io/name | head -20

# 3. Verify alerts showing
curl -s https://fleet-status-route/api/v1/alerts | jq .alerts

# 4. Test high CPU detection
# Nodes with CPU >= CPU_WARNING should appear in dashboard
```

## Performance Considerations

- **Query aggregation**: All queries fetch all clusters/nodes in one request
- **Caching**: 30-second TTL prevents excessive Thanos load
- **Async queries**: Parallel query execution via asyncio
- **Metrics staleness**: 5-minute threshold marks data as stale

## Security

- Bearer token stored in OpenShift Secret (not ConfigMap)
- Token never exposed to frontend
- All Thanos communication through backend
- TLS verification enabled by default
- RBAC limits to read-only operations

## License

Proprietary - Red Hat

## Support

For issues:
1. Check `/api/v1/health` endpoint
2. Review backend logs: `oc logs -f deployment/fleet-status-backend -n fleet-status`
3. Verify Thanos connectivity from backend pod
4. Check that RHACM Observability is running and collecting metrics
