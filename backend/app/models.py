from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class NodeMetrics(BaseModel):
    name: str
    role: Optional[str] = None
    ready: bool
    schedulable: bool
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    cpu_requests_percent: Optional[float] = None
    cpu_limits_percent: Optional[float] = None
    memory_requests_percent: Optional[float] = None
    memory_limits_percent: Optional[float] = None
    alerts_count: int = 0
    uptime_seconds: Optional[int] = None


class ClusterMetrics(BaseModel):
    name: str
    cluster_id: str
    version: Optional[str] = None
    vendor: Optional[str] = None
    cloud: Optional[str] = None
    status: str
    available: bool

    nodes: Dict[str, Any] = {
        "total": 0,
        "ready": 0,
        "not_ready": 0,
        "schedulable": 0,
        "unschedulable": 0
    }

    cpu: Dict[str, Any] = {
        "average_percent": None,
        "peak_percent": None,
        "highest_node": None,
        "high_cpu_nodes": 0
    }

    memory: Dict[str, Any] = {
        "average_percent": None,
        "peak_percent": None,
        "highest_node": None
    }

    alerts: Dict[str, int] = {
        "critical": 0,
        "warning": 0,
        "info": 0
    }

    metrics: Dict[str, Any] = {
        "last_received": None,
        "age_seconds": None,
        "stale": False
    }


class FleetMetrics(BaseModel):
    timestamp: datetime

    clusters: Dict[str, int] = {
        "total": 0,
        "healthy": 0,
        "warning": 0,
        "critical": 0,
        "no_data": 0
    }

    nodes: Dict[str, int] = {
        "total": 0,
        "ready": 0,
        "not_ready": 0,
        "schedulable": 0,
        "unschedulable": 0
    }

    cpu: Dict[str, Any] = {
        "average_percent": None,
        "highest_percent": None,
        "high_cpu_nodes": 0
    }

    memory: Dict[str, Any] = {
        "average_percent": None,
        "highest_percent": None
    }

    alerts: Dict[str, int] = {
        "total": 0,
        "critical": 0,
        "warning": 0,
        "info": 0
    }

    status: str


class AlertInfo(BaseModel):
    alertname: str
    severity: str
    cluster: Optional[str] = None
    node: Optional[str] = None
    namespace: Optional[str] = None
    pod: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    thanos_connected: bool
    clusters_discovered: int
    metrics_available: List[str]
    metrics_unavailable: List[str]
    cluster_label: Optional[str] = None
    node_label: Optional[str] = None
