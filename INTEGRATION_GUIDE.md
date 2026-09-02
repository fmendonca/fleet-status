# RHACM Integration Guide

Step-by-step guide to integrate Fleet Status Dashboard with your RHACM environment.

## Prerequisites

- Red Hat OpenShift 4.20 (hub cluster) - or 4.15+
- ACM (RHACM) 2.16 with Observability enabled - or 2.5+
- At least 2 managed clusters registered
- kubectl/oc CLI v4.20+ with admin access to hub cluster
- Podman or Docker for building images
- GitHub account with push access to deploy repo

## Step 1: Verify RHACM Observability Setup

### Check if RHACM is installed
```bash
oc get mco -A
```

Expected output:
```
NAMESPACE                             NAME      AGE
open-cluster-management               observability   5d
```

### Verify MultiClusterObservability is enabled
```bash
oc get mco -o yaml | grep -A5 "status:"
```

Should show:
```yaml
status:
  conditions:
  - message: MultiClusterObservability is running
    type: Ready
```

### Check Observability namespace
```bash
oc get pods -n open-cluster-management-observability
```

Expected components:
- `thanos-query-*` (Thanos query service)
- `rbac-query-proxy-*` (RBAC-protected proxy)
- `prometheus-*` (Prometheus)
- `alertmanager-*` (Alertmanager)

## Step 2: Get Thanos Credentials

### Find rbac-query-proxy route
```bash
THANOS_HOST=$(oc get route rbac-query-proxy \
  -n open-cluster-management-observability \
  -o jsonpath='{.spec.host}')

THANOS_URL="https://${THANOS_HOST}"
echo "THANOS_URL=${THANOS_URL}"
```

### Get service account token
The dashboard will use the service account created in OpenShift. Get token from the deployed pod:

```bash
POD=$(oc get pods -n fleet-status -l component=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
  echo "Backend not deployed yet. Use a temporary token:"
  oc whoami -t
else
  oc exec -it $POD -n fleet-status -- cat /var/run/secrets/kubernetes.io/serviceaccount/token
fi
```

Or create a dedicated service account:

```bash
# In the hub cluster
oc create serviceaccount fleet-status-reader -n open-cluster-management-observability

# Grant access to rbac-query-proxy (needs RHACM RBAC configuration)
oc policy add-role-to-user edit fleet-status-reader -n open-cluster-management-observability
```

### Test connectivity
```bash
TOKEN=$(oc whoami -t)
THANOS_URL="https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local"

# Test without TLS (inside cluster)
curl -k -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/query?query=up" \
  | jq '.data.result | length'
```

Should return > 0 results.

## Step 3: Configure Secret for Backend

### Create the secret
```bash
kubectl create secret generic fleet-status-backend-secret \
  -n fleet-status \
  --from-literal=THANOS_URL="https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local" \
  --from-literal=THANOS_TOKEN="$(oc whoami -t)" \
  --from-literal=THANOS_TLS_VERIFY="true" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Verify secret
```bash
oc get secret fleet-status-backend-secret -n fleet-status -o jsonpath='{.data.THANOS_URL}' | base64 -d
```

## Step 4: Build Container Images

### Clone repository
```bash
git clone https://github.com/fmendonca/fleet-status.git
cd fleet-status
```

### Build backend image
```bash
REGISTRY=quay.io/your-username
VERSION=v1.0

cd backend
podman build -t ${REGISTRY}/fleet-status-backend:${VERSION} .
podman push ${REGISTRY}/fleet-status-backend:${VERSION}
cd ..
```

### Build frontend image
```bash
cd frontend
podman build -t ${REGISTRY}/fleet-status-frontend:${VERSION} .
podman push ${REGISTRY}/fleet-status-frontend:${VERSION}
cd ..
```

## Step 5: Deploy to OpenShift

### Update image references
Edit `openshift/backend-deployment.yaml` and `openshift/frontend-deployment.yaml`:

```bash
sed -i "s|quay.io/fleet-status|${REGISTRY}|g" openshift/*.yaml
```

### Create namespace and deploy
```bash
# Create namespace
oc create namespace fleet-status --dry-run=client -o yaml | oc apply -f -

# Apply ConfigMap
oc apply -f openshift/configmap.yaml

# Apply Secret (already created above)
# oc apply -f openshift/secret.yaml

# Apply RBAC
oc apply -f openshift/rbac.yaml

# Deploy backend
oc apply -f openshift/backend-deployment.yaml

# Deploy frontend and route
oc apply -f openshift/frontend-deployment.yaml
```

### Wait for deployments
```bash
oc rollout status deployment/fleet-status-backend -n fleet-status
oc rollout status deployment/fleet-status-frontend -n fleet-status
```

### Get dashboard URL
```bash
oc get route fleet-status -n fleet-status -o jsonpath='https://{.spec.host}{"\n"}'
```

## Step 6: Verify Deployment

### Check pod status
```bash
oc get pods -n fleet-status
```

All pods should be `Running` and `Ready`.

### Check backend logs
```bash
oc logs -f deployment/fleet-status-backend -n fleet-status
```

Look for messages like:
```
RHACM Thanos connected successfully
Cluster label detected: cluster
Clusters discovered: 24
Available metrics: acm_managed_cluster_info, kube_node_info, ...
```

### Test API endpoints
```bash
BACKEND_POD=$(oc get pods -n fleet-status -l component=backend -o jsonpath='{.items[0].metadata.name}')

# Test health
oc exec -it $BACKEND_POD -n fleet-status -- curl -s http://localhost:8000/healthz | jq .

# Test fleet metrics
oc exec -it $BACKEND_POD -n fleet-status -- curl -s http://localhost:8000/api/v1/fleet | jq '.clusters'

# Test cluster discovery
oc exec -it $BACKEND_POD -n fleet-status -- curl -s http://localhost:8000/api/v1/clusters | jq '.clusters | length'
```

### Access dashboard
Open in browser: `https://<route-from-step-above>`

Should show:
- Overall fleet summary
- List of all clusters
- Status indicators (healthy/warning/critical)
- Node and alert counts

## Step 7: Validate Accuracy

### Compare cluster counts
```bash
# Count managed clusters in RHACM
RHACM_CLUSTERS=$(oc get managedclusters | grep -v NAME | wc -l)

# Get from dashboard API
DASHBOARD_CLUSTERS=$(oc exec -it $BACKEND_POD -n fleet-status -- \
  curl -s http://localhost:8000/api/v1/fleet | jq .clusters.total)

echo "RHACM: $RHACM_CLUSTERS"
echo "Dashboard: $DASHBOARD_CLUSTERS"
[ "$RHACM_CLUSTERS" -eq "$DASHBOARD_CLUSTERS" ] && echo "✓ Match" || echo "✗ Mismatch"
```

### Compare node counts
```bash
# From RHACM
oc get nodes -A | tail -n +2 | wc -l

# From dashboard
oc exec -it $BACKEND_POD -n fleet-status -- \
  curl -s http://localhost:8000/api/v1/fleet | jq .nodes.total
```

### Verify alerts
```bash
# Check if alerts are being reported
oc exec -it $BACKEND_POD -n fleet-status -- \
  curl -s http://localhost:8000/api/v1/alerts | jq '.alerts | length'
```

Should show > 0 if there are firing alerts.

## Step 8: Configure for Production

### Scale backend (optional HA)
```bash
oc scale deployment fleet-status-backend --replicas=2 -n fleet-status
```

### Increase frontend replicas
```bash
oc scale deployment fleet-status-frontend --replicas=3 -n fleet-status
```

### Enable TLS termination
Already configured in Route with edge termination.

### Add monitoring
```bash
# Scrape dashboard metrics with Prometheus
cat <<EOF | oc apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: fleet-status-backend
  namespace: fleet-status
spec:
  selector:
    matchLabels:
      app: fleet-status
      component: backend
  endpoints:
  - port: http
    interval: 30s
    path: /metrics
EOF
```

## Troubleshooting

### Backend can't connect to Thanos
```bash
# Test from backend pod
POD=$(oc get pods -n fleet-status -l component=backend -o jsonpath='{.items[0].metadata.name}')

oc exec -it $POD -n fleet-status -- \
  curl -k -H "Authorization: Bearer $THANOS_TOKEN" \
  https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local/api/v1/labels
```

If fails:
1. Verify token is valid: `oc whoami -t`
2. Check Thanos pods running: `oc get pods -n open-cluster-management-observability`
3. Check network policies: `oc get networkpolicies -n fleet-status`

### Cluster discovery shows 0 clusters
1. Verify RHACM has clusters registered: `oc get managedclusters`
2. Check backend logs for discovery errors: `oc logs deployment/fleet-status-backend -n fleet-status | grep -i discover`
3. Test PromQL directly:
```bash
POD=$(oc get pods -n fleet-status -l component=backend -o jsonpath='{.items[0].metadata.name}')
oc exec -it $POD -n fleet-status -- \
  curl -k -H "Authorization: Bearer $THANOS_TOKEN" \
  "https://rbac-query-proxy.open-cluster-management-observability.svc.cluster.local/api/v1/query?query=count(acm_managed_cluster_info)"
```

### Dashboard shows "NO_DATA" for all clusters
1. Verify metrics are being collected: `oc get pods -n open-cluster-management-observability | grep prometheus`
2. Check that spoke clusters are connected to hub
3. Wait 5-10 minutes for metrics to flow through Thanos

### High API latency
1. Check backend resource usage: `oc top pods -n fleet-status`
2. Increase replicas if CPU/memory high
3. Check Thanos performance: `oc logs deployment/thanos-query -n open-cluster-management-observability | tail -100`

## Next Steps

1. **Customize thresholds** - Edit ConfigMap to adjust warning/critical levels
2. **Add RBAC** - Integrate with OpenShift authentication
3. **Setup alerts** - Configure Alertmanager to notify on critical events
4. **Backup metrics** - Export historical data to long-term storage
5. **Integrate with ChatOps** - Add Slack/Teams notifications

## Support

For issues:
1. Check dashboard at `/api/v1/health`
2. Review backend logs
3. Test Thanos connectivity separately
4. Check RHACM Observability status
5. File issue on GitHub with logs and RHACM version
