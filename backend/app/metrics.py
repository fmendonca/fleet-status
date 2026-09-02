import logging
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from app.thanos import thanos_client
from app.discovery import discovery
from app.config import settings

logger = logging.getLogger(__name__)


class MetricsService:
    def __init__(self):
        self.cluster_label: Optional[str] = None
        self.node_label: Optional[str] = None
        self.available_metrics: Set[str] = set()
        self.unavailable_metrics: Set[str] = set()

    async def _metric_exists(self, metric_name: str) -> bool:
        """Check if metric exists in Thanos"""
        try:
            result = await thanos_client.series([metric_name])
            exists = result.get("status") == "success" and len(result.get("data", [])) > 0

            if exists:
                self.available_metrics.add(metric_name)
            else:
                self.unavailable_metrics.add(metric_name)

            return exists
        except Exception as e:
            logger.warning(f"Could not check metric {metric_name}: {e}")
            self.unavailable_metrics.add(metric_name)
            return False

    async def initialize(self):
        """Initialize metrics service"""
        self.cluster_label = discovery.cluster_label
        self.node_label = discovery.node_label

        metrics_to_check = [
            "acm_managed_cluster_info",
            "kube_node_info",
            "kube_node_status_condition",
            "kube_node_spec_unschedulable",
            "node_cpu_seconds_total",
            "node_memory_MemAvailable_bytes",
            "node_memory_MemTotal_bytes",
            "ALERTS"
        ]

        for metric in metrics_to_check:
            await self._metric_exists(metric)

    async def get_cluster_count(self) -> int:
        """Get total number of clusters"""
        try:
            result = await thanos_client.query(
                f"count(acm_managed_cluster_info)"
            )
            if result.get("status") == "success":
                data = result.get("data", {}).get("result", [])
                if data:
                    return int(float(data[0].get("value", [None, "0"])[1]))
        except Exception as e:
            logger.error(f"Error getting cluster count: {e}")
        return 0

    async def get_node_count_by_cluster(self) -> Dict[str, int]:
        """Get node count per cluster"""
        if not self.cluster_label:
            return {}

        try:
            promql = f"count by ({self.cluster_label}) (kube_node_info)"
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            counts = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                cluster = series.get("metric", {}).get(self.cluster_label, "unknown")
                value = int(float(series.get("value", [None, "0"])[1]))
                counts[cluster] = value

            return counts
        except Exception as e:
            logger.error(f"Error getting node counts: {e}")
            return {}

    async def get_node_ready_by_cluster(self) -> Dict[str, int]:
        """Get ready node count per cluster"""
        if not self.cluster_label:
            return {}

        try:
            promql = f"""sum by ({self.cluster_label}) (
                kube_node_status_condition{{
                    condition="Ready",
                    status="true"
                }}
            )"""
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            counts = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                cluster = series.get("metric", {}).get(self.cluster_label, "unknown")
                value = int(float(series.get("value", [None, "0"])[1]))
                counts[cluster] = value

            return counts
        except Exception as e:
            logger.error(f"Error getting ready nodes: {e}")
            return {}

    async def get_node_unschedulable_by_cluster(self) -> Dict[str, int]:
        """Get unschedulable node count per cluster"""
        if not self.cluster_label:
            return {}

        try:
            promql = f"""sum by ({self.cluster_label}) (
                kube_node_spec_unschedulable
            )"""
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            counts = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                cluster = series.get("metric", {}).get(self.cluster_label, "unknown")
                value = int(float(series.get("value", [None, "0"])[1]))
                counts[cluster] = value

            return counts
        except Exception as e:
            logger.error(f"Error getting unschedulable nodes: {e}")
            return {}

    async def get_cpu_by_node(self) -> Dict[str, Dict[str, float]]:
        """Get CPU utilization per node per cluster"""
        if not self.cluster_label or not self.node_label:
            return {}

        try:
            promql = f"""100 - (
                avg by ({self.cluster_label}, {self.node_label}) (
                    rate(node_cpu_seconds_total{{mode="idle"}}[5m])
                ) * 100
            )"""
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            cpu_data = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                metric = series.get("metric", {})
                cluster = metric.get(self.cluster_label, "unknown")
                node = metric.get(self.node_label, "unknown")
                cpu_value = float(series.get("value", [None, "0"])[1])

                if cluster not in cpu_data:
                    cpu_data[cluster] = {}
                cpu_data[cluster][node] = max(0, min(100, cpu_value))

            return cpu_data
        except Exception as e:
            logger.error(f"Error getting CPU data: {e}")
            return {}

    async def get_memory_by_node(self) -> Dict[str, Dict[str, float]]:
        """Get memory utilization per node per cluster"""
        if not self.cluster_label or not self.node_label:
            return {}

        try:
            promql = f"""100 * (
                1 - (
                    node_memory_MemAvailable_bytes
                    /
                    node_memory_MemTotal_bytes
                )
            )"""
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            memory_data = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                metric = series.get("metric", {})
                cluster = metric.get(self.cluster_label, "unknown")
                node = metric.get(self.node_label, "unknown")
                memory_value = float(series.get("value", [None, "0"])[1])

                if cluster not in memory_data:
                    memory_data[cluster] = {}
                memory_data[cluster][node] = max(0, min(100, memory_value))

            return memory_data
        except Exception as e:
            logger.error(f"Error getting memory data: {e}")
            return {}

    async def get_alerts_by_cluster(self) -> Dict[str, Dict[str, int]]:
        """Get alert counts per cluster"""
        if not self.cluster_label:
            return {}

        ignore_list = settings.alert_ignore_list.split(",")

        try:
            promql = f"""count by ({self.cluster_label}, severity) (
                ALERTS{{alertstate="firing"}}
            )"""
            result = await thanos_client.query(promql)

            if result.get("status") != "success":
                return {}

            alerts = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                metric = series.get("metric", {})
                alert_name = metric.get("alertname", "")

                if any(ignored in alert_name for ignored in ignore_list):
                    continue

                cluster = metric.get(self.cluster_label, "unknown")
                severity = metric.get("severity", "info").lower()
                count = int(float(series.get("value", [None, "0"])[1]))

                if cluster not in alerts:
                    alerts[cluster] = {"critical": 0, "warning": 0, "info": 0}

                if severity in alerts[cluster]:
                    alerts[cluster][severity] += count

            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return {}

    async def get_metric_timestamp_by_cluster(self) -> Dict[str, datetime]:
        """Get last metric timestamp per cluster"""
        if not self.cluster_label:
            return {}

        try:
            result = await thanos_client.query(f"acm_managed_cluster_info")

            if result.get("status") != "success":
                return {}

            timestamps = {}
            data = result.get("data", {}).get("result", [])
            for series in data:
                cluster = series.get("metric", {}).get(self.cluster_label, "unknown")
                timestamp = int(float(series.get("value", [None, "0"])[0]))
                timestamps[cluster] = datetime.fromtimestamp(timestamp)

            return timestamps
        except Exception as e:
            logger.error(f"Error getting metric timestamps: {e}")
            return {}


metrics_service = MetricsService()
