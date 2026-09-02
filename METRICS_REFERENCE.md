# Metrics Reference

This document lists all PromQL metrics used by the Fleet Status Dashboard and how to verify they're available in your RHACM Thanos instance.

## Cluster Discovery

### Query
```promql
acm_managed_cluster_info
```

### Purpose
Discover all managed clusters and extract metadata.

### Label priorities (auto-detected)
1. `cluster`
2. `cluster_name`
3. `managed_cluster`
4. `managed_cluster_name`
5. `cluster_namespace`
6. `name`
7. `managed_cluster_id`

### Example result
```
acm_managed_cluster_info{
  cluster="ocp-prod-us",
  version="4.13.0",
  vendor="OpenShift",
  cloud="AWS"
} 1
```

### Verification
```bash
# Quick test
curl -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/query?query=acm_managed_cluster_info" \
  | jq '.data.result[0].metric'
```

---

## Node Metrics

### Node Count
```promql
count by (<cluster_label>) (kube_node_info)
```

**Metric**: `kube_node_info`
**Labels**: `cluster`, `node`, `kubernetes_version`, `kubelet_version`, etc.

### Node Ready Status
```promql
sum by (<cluster_label>) (
  kube_node_status_condition{
    condition="Ready",
    status="true"
  }
)
```

**Metric**: `kube_node_status_condition`
**Labels**: `cluster`, `node`, `condition` (Ready|NotReady), `status` (true|false)

### Node Unschedulable
```promql
sum by (<cluster_label>) (
  kube_node_spec_unschedulable
)
```

**Metric**: `kube_node_spec_unschedulable`
**Labels**: `cluster`, `node`
**Value**: 0 (schedulable) or 1 (unschedulable)

### Node Role
```promql
kube_node_labels{label_node_role_kubernetes_io_master=""}
kube_node_labels{label_node_role_kubernetes_io_worker=""}
```

**Metric**: `kube_node_labels`
**Available**: Optional, used for filtering

---

## CPU Metrics

### CPU Utilization (%)
```promql
100 - (
  avg by (<cluster_label>, <node_label>) (
    rate(
      node_cpu_seconds_total{
        mode="idle"
      }[5m]
    )
  ) * 100
)
```

**Base metric**: `node_cpu_seconds_total`
**Labels**: `cluster`, `instance` (or `node`), `cpu`, `mode`
**Modes**: user, system, idle, iowait, irq, softirq, steal, guest

### CPU Capacity
```promql
kube_node_status_capacity{
  resource="cpu"
}
```

**Metric**: `kube_node_status_capacity`
**Labels**: `cluster`, `node`, `resource` (cpu|memory)

### CPU Allocatable
```promql
kube_node_status_allocatable{
  resource="cpu"
}
```

**Metric**: `kube_node_status_allocatable`
**Labels**: `cluster`, `node`, `resource`

### CPU Requests
```promql
sum by (node, cluster) (
  kube_pod_container_resource_requests{
    resource="cpu"
  }
)
```

**Metric**: `kube_pod_container_resource_requests`
**Labels**: `cluster`, `node`, `namespace`, `pod`, `container`, `resource`

### CPU Limits
```promql
sum by (node, cluster) (
  kube_pod_container_resource_limits{
    resource="cpu"
  }
)
```

**Metric**: `kube_pod_container_resource_limits`
**Labels**: `cluster`, `node`, `namespace`, `pod`, `container`, `resource`

---

## Memory Metrics

### Memory Utilization (%)
```promql
100 * (
  1 - (
    node_memory_MemAvailable_bytes
    /
    node_memory_MemTotal_bytes
  )
)
```

**Metrics**:
- `node_memory_MemAvailable_bytes`
- `node_memory_MemTotal_bytes`

**Labels**: `cluster`, `instance` (or `node`)

### Memory Capacity
```promql
kube_node_status_capacity{
  resource="memory"
}
```

### Memory Allocatable
```promql
kube_node_status_allocatable{
  resource="memory"
}
```

### Memory Requests
```promql
sum by (node, cluster) (
  kube_pod_container_resource_requests{
    resource="memory"
  }
)
```

### Memory Limits
```promql
sum by (node, cluster) (
  kube_pod_container_resource_limits{
    resource="memory"
  }
)
```

---

## Alert Metrics

### Firing Alerts
```promql
ALERTS{
  alertstate="firing"
}
```

**Metric**: `ALERTS` (from Prometheus alertmanager)
**Labels**: 
- `alertname` (e.g., "KubeNodeNotReady")
- `severity` (critical, warning, info)
- `cluster`
- `instance` (optional)
- `namespace` (optional)
- `pod` (optional)
- `node` (optional)

### Alert Count by Cluster and Severity
```promql
count by (<cluster_label>, severity) (
  ALERTS{
    alertstate="firing"
  }
)
```

### Alert Names (common)
```
KubeNodeNotReady
KubeNodeUnreachable
KubeNodeMemoryPressure
KubeNodeDiskPressure
KubeNodePIDPressure
KubePodCrashLooping
KubePodNotHealthy
KubeCpuUsageHigh
KubeMemoryUsageHigh
KubeDeploymentGenerationMismatch
KubePersistentvolumeclaimPending
KubeStatefulsetGenerationMismatch
```

---

## Verification Commands

### Test Thanos connectivity
```bash
TOKEN=$(oc whoami -t)
THANOS_URL=$(oc get route rbac-query-proxy \
  -n open-cluster-management-observability \
  -o jsonpath='https://{.spec.host}')

curl -k -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/labels" | jq '.data'
```

### Check available metrics
```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/series?match[]=acm_managed_cluster_info" \
  | jq '.data | length'
```

### Query clusters
```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/query?query=count(acm_managed_cluster_info)" \
  | jq '.data.result[0].value[1]'
```

### Query nodes in cluster
```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  "${THANOS_URL}/api/v1/query?query=kube_node_info" \
  | jq '.data.result | length'
```

---

## Allowlist Configuration

If metrics are unavailable, they may need to be added to RHACM's observability allowlist:

### Check current allowlist
```bash
oc get observabilitymetricallowlist \
  -n open-cluster-management-observability -o yaml
```

### Add custom metrics (if needed)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: observability-metrics-custom-allowlist
  namespace: open-cluster-management-observability
data:
  metrics.txt: |
    node_cpu_seconds_total
    node_memory_MemAvailable_bytes
    node_memory_MemTotal_bytes
    kube_node_info
    kube_node_status_condition
    kube_node_spec_unschedulable
    acm_managed_cluster_info
    ALERTS
```

---

## Metric Availability by RHACM Version

| Metric | 2.5 | 2.6 | 2.7 | 2.8 | 2.9 |
|--------|-----|-----|-----|-----|-----|
| acm_managed_cluster_info | ✓ | ✓ | ✓ | ✓ | ✓ |
| kube_node_info | ✓ | ✓ | ✓ | ✓ | ✓ |
| kube_node_status_condition | ✓ | ✓ | ✓ | ✓ | ✓ |
| node_cpu_seconds_total | ✓ | ✓ | ✓ | ✓ | ✓ |
| node_memory_* | ✓ | ✓ | ✓ | ✓ | ✓ |
| ALERTS | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Troubleshooting

### Empty results
1. Verify token has proper permissions
2. Check Thanos URL is accessible
3. Confirm metrics are being collected on clusters
4. Wait 2-5 minutes after RHACM installation

### High latency
1. Thanos can be slow with many clusters/nodes
2. Try with smaller time ranges in test queries
3. Increase backend query timeout if needed

### Label not found
1. Check `discovery.py` for label detection logic
2. Manually inspect query results to find actual label
3. Update `CLUSTER_LABEL_CANDIDATES` or `NODE_LABEL_CANDIDATES`

### Missing metrics
1. Verify in allowlist configuration
2. Check RHACM Observability pods are running
3. Check spoke cluster metrics collection
