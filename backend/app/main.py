import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

from app.config import settings
from app.discovery import discovery
from app.metrics import metrics_service
from app.cache import cache
from app.health import health_calc
from app.models import FleetMetrics, ClusterMetrics, HealthResponse
from app.thanos import thanos_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenShift Fleet Status Dashboard",
    description="Multi-cluster monitoring for RHACM",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_duration = Histogram(
    'thanos_query_duration_seconds',
    'Thanos query duration',
    ['query_name']
)

query_errors = Counter(
    'thanos_query_errors_total',
    'Thanos query errors',
    ['query_name']
)

clusters_total = Gauge(
    'dashboard_clusters_total',
    'Total clusters discovered'
)

nodes_total = Gauge(
    'dashboard_nodes_total',
    'Total nodes in fleet'
)

high_cpu_nodes = Gauge(
    'dashboard_high_cpu_nodes',
    'Nodes with high CPU'
)

critical_clusters = Gauge(
    'dashboard_critical_clusters',
    'Clusters with critical status'
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=== Fleet Status Dashboard Startup ===")

    if settings.mock_mode:
        logger.warning("MOCK_MODE enabled - using simulated data")
        return

    logger.info("Initializing cluster discovery...")
    await discovery.initialize()

    logger.info("Initializing metrics service...")
    await metrics_service.initialize()

    logger.info("Checking Thanos connectivity...")
    if await thanos_client.is_available():
        logger.info("✓ RHACM Thanos connected successfully")
    else:
        logger.error("✗ Failed to connect to Thanos")

    logger.info(f"Cluster label detected: {discovery.cluster_label}")
    logger.info(f"Node label detected: {discovery.node_label}")
    logger.info(f"Clusters discovered: {len(discovery.discovered_clusters)}")

    logger.info("Available metrics:")
    for metric in sorted(metrics_service.available_metrics):
        logger.info(f"  ✓ {metric}")

    if metrics_service.unavailable_metrics:
        logger.warning("Unavailable metrics:")
        for metric in sorted(metrics_service.unavailable_metrics):
            logger.warning(f"  ✗ {metric}")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    if settings.mock_mode:
        return {"status": "ready"}

    if await thanos_client.is_available():
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Thanos unavailable")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """Diagnostics endpoint"""
    thanos_ok = await thanos_client.is_available() if not settings.mock_mode else True

    return HealthResponse(
        status="ok" if thanos_ok else "degraded",
        thanos_connected=thanos_ok,
        clusters_discovered=len(discovery.discovered_clusters),
        metrics_available=sorted(list(metrics_service.available_metrics)),
        metrics_unavailable=sorted(list(metrics_service.unavailable_metrics)),
        cluster_label=discovery.cluster_label,
        node_label=discovery.node_label
    )


@app.get("/api/v1/fleet", response_model=FleetMetrics)
async def get_fleet():
    """Get overall fleet status"""
    cache_key = "fleet_metrics"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if settings.mock_mode:
        return _get_fleet_mock()

    try:
        node_counts = await metrics_service.get_node_count_by_cluster()
        ready_nodes = await metrics_service.get_node_ready_by_cluster()
        unschedulable_nodes = await metrics_service.get_node_unschedulable_by_cluster()
        cpu_by_node = await metrics_service.get_cpu_by_node()
        memory_by_node = await metrics_service.get_memory_by_node()
        alerts = await metrics_service.get_alerts_by_cluster()

        total_clusters = len(discovery.discovered_clusters)
        total_nodes = sum(node_counts.values())
        total_ready = sum(ready_nodes.values())
        total_unschedulable = sum(unschedulable_nodes.values())
        total_not_ready = total_nodes - total_ready

        cpu_values = []
        for cluster_cpus in cpu_by_node.values():
            cpu_values.extend(cluster_cpus.values())

        memory_values = []
        for cluster_mems in memory_by_node.values():
            memory_values.extend(cluster_mems.values())

        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        cpu_peak = max(cpu_values) if cpu_values else 0
        memory_avg = sum(memory_values) / len(memory_values) if memory_values else 0
        memory_peak = max(memory_values) if memory_values else 0

        high_cpu_count = sum(1 for v in cpu_values if v >= settings.cpu_warning)
        total_alerts = sum(sum(a.values()) for a in alerts.values())
        total_critical = sum(a.get("critical", 0) for a in alerts.values())
        total_warning = sum(a.get("warning", 0) for a in alerts.values())
        total_info = sum(a.get("info", 0) for a in alerts.values())

        healthy = 0
        warning = 0
        critical = 0
        no_data = 0

        for cluster in discovery.discovered_clusters:
            if cluster not in node_counts:
                no_data += 1
            elif cluster not in alerts or (alerts[cluster]["critical"] == 0 and alerts[cluster]["warning"] == 0):
                healthy += 1
            elif alerts[cluster].get("critical", 0) > 0:
                critical += 1
            else:
                warning += 1

        fleet_metrics = FleetMetrics(
            timestamp=datetime.now(),
            clusters={
                "total": total_clusters,
                "healthy": healthy,
                "warning": warning,
                "critical": critical,
                "no_data": no_data
            },
            nodes={
                "total": total_nodes,
                "ready": total_ready,
                "not_ready": total_not_ready,
                "schedulable": total_nodes - total_unschedulable,
                "unschedulable": total_unschedulable
            },
            cpu={
                "average_percent": round(cpu_avg, 2),
                "highest_percent": round(cpu_peak, 2),
                "high_cpu_nodes": high_cpu_count
            },
            memory={
                "average_percent": round(memory_avg, 2),
                "highest_percent": round(memory_peak, 2)
            },
            alerts={
                "total": total_alerts,
                "critical": total_critical,
                "warning": total_warning,
                "info": total_info
            },
            status="CRITICAL" if critical > 0 else "WARNING" if warning > 0 else "HEALTHY"
        )

        cache.set(cache_key, fleet_metrics)

        clusters_total.set(total_clusters)
        nodes_total.set(total_nodes)
        high_cpu_nodes.set(high_cpu_count)
        critical_clusters.set(critical)

        return fleet_metrics

    except Exception as e:
        logger.error(f"Error getting fleet metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/clusters")
async def get_clusters():
    """Get all clusters with basic info"""
    try:
        clusters = []
        for cluster_name in sorted(discovery.discovered_clusters):
            cluster_info = {
                "name": cluster_name,
                "id": cluster_name
            }
            clusters.append(cluster_info)

        return {"clusters": clusters}
    except Exception as e:
        logger.error(f"Error getting clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    """Get detailed cluster info"""
    try:
        if cluster_id not in discovery.discovered_clusters:
            raise HTTPException(status_code=404, detail="Cluster not found")

        node_counts = await metrics_service.get_node_count_by_cluster()
        ready_nodes = await metrics_service.get_node_ready_by_cluster()
        unschedulable = await metrics_service.get_node_unschedulable_by_cluster()
        cpu_data = await metrics_service.get_cpu_by_node()
        memory_data = await metrics_service.get_memory_by_node()
        alerts = await metrics_service.get_alerts_by_cluster()

        total_nodes = node_counts.get(cluster_id, 0)
        ready = ready_nodes.get(cluster_id, 0)
        unsch = unschedulable.get(cluster_id, 0)

        cluster_cpus = cpu_data.get(cluster_id, {})
        cluster_mems = memory_data.get(cluster_id, {})

        cpu_avg = sum(cluster_cpus.values()) / len(cluster_cpus) if cluster_cpus else None
        cpu_peak = max(cluster_cpus.values()) if cluster_cpus else None
        peak_cpu_node = max(cluster_cpus, key=cluster_cpus.get) if cluster_cpus else None

        memory_avg = sum(cluster_mems.values()) / len(cluster_mems) if cluster_mems else None
        memory_peak = max(cluster_mems.values()) if cluster_mems else None
        peak_mem_node = max(cluster_mems, key=cluster_mems.get) if cluster_mems else None

        cluster_alerts = alerts.get(cluster_id, {"critical": 0, "warning": 0, "info": 0})

        cluster = ClusterMetrics(
            name=cluster_id,
            cluster_id=cluster_id,
            available=True,
            status="HEALTHY",
            nodes={
                "total": total_nodes,
                "ready": ready,
                "not_ready": total_nodes - ready,
                "schedulable": total_nodes - unsch,
                "unschedulable": unsch
            },
            cpu={
                "average_percent": round(cpu_avg, 2) if cpu_avg else None,
                "peak_percent": round(cpu_peak, 2) if cpu_peak else None,
                "highest_node": peak_cpu_node,
                "high_cpu_nodes": sum(1 for v in cluster_cpus.values() if v >= settings.cpu_warning)
            },
            memory={
                "average_percent": round(memory_avg, 2) if memory_avg else None,
                "peak_percent": round(memory_peak, 2) if memory_peak else None,
                "highest_node": peak_mem_node
            },
            alerts=cluster_alerts,
            metrics={
                "last_received": datetime.now().isoformat(),
                "age_seconds": 0,
                "stale": False
            }
        )

        return cluster.dict()

    except Exception as e:
        logger.error(f"Error getting cluster {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/clusters/{cluster_id}/nodes")
async def get_cluster_nodes(cluster_id: str):
    """Get nodes in a cluster"""
    try:
        if cluster_id not in discovery.discovered_clusters:
            raise HTTPException(status_code=404, detail="Cluster not found")

        cpu_data = await metrics_service.get_cpu_by_node()
        memory_data = await metrics_service.get_memory_by_node()

        cluster_cpus = cpu_data.get(cluster_id, {})
        cluster_mems = memory_data.get(cluster_id, {})

        nodes = []
        all_nodes = set(cluster_cpus.keys()) | set(cluster_mems.keys())

        for node_name in sorted(all_nodes):
            nodes.append({
                "name": node_name,
                "ready": True,
                "schedulable": True,
                "cpu_percent": cluster_cpus.get(node_name),
                "memory_percent": cluster_mems.get(node_name),
                "cpu_class": health_calc.classify_cpu(cluster_cpus.get(node_name, 0)),
                "memory_class": health_calc.classify_memory(cluster_mems.get(node_name, 0))
            })

        return {"nodes": nodes}

    except Exception as e:
        logger.error(f"Error getting cluster nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/alerts")
async def get_alerts():
    """Get all firing alerts"""
    try:
        alerts_by_cluster = await metrics_service.get_alerts_by_cluster()

        alerts_list = []
        for cluster, severity_counts in alerts_by_cluster.items():
            for severity, count in severity_counts.items():
                if count > 0:
                    alerts_list.append({
                        "cluster": cluster,
                        "severity": severity,
                        "count": count
                    })

        return {"alerts": alerts_list}

    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return prometheus_client.generate_latest()


def _get_fleet_mock() -> FleetMetrics:
    """Generate mock fleet metrics for development"""
    return FleetMetrics(
        timestamp=datetime.now(),
        clusters={"total": 24, "healthy": 21, "warning": 2, "critical": 1, "no_data": 0},
        nodes={"total": 318, "ready": 316, "not_ready": 2, "schedulable": 313, "unschedulable": 5},
        cpu={"average_percent": 43.8, "highest_percent": 94.2, "high_cpu_nodes": 4},
        memory={"average_percent": 57.2, "highest_percent": 91.4},
        alerts={"total": 18, "critical": 2, "warning": 11, "info": 5},
        status="WARNING"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
