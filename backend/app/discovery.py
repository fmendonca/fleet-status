import logging
from typing import Optional, List, Dict, Set
from app.thanos import thanos_client

logger = logging.getLogger(__name__)

CLUSTER_LABEL_CANDIDATES = [
    "cluster",
    "cluster_name",
    "managed_cluster",
    "managed_cluster_name",
    "cluster_namespace",
    "name",
    "managed_cluster_id"
]

NODE_LABEL_CANDIDATES = [
    "node",
    "node_name",
    "instance",
    "kubernetes_node"
]


class Discovery:
    def __init__(self):
        self.cluster_label: Optional[str] = None
        self.node_label: Optional[str] = None
        self.discovered_clusters: Set[str] = set()

    async def detect_cluster_label(self) -> Optional[str]:
        """Dynamically detect which label RHACM uses for cluster identification"""
        if self.cluster_label:
            return self.cluster_label

        try:
            result = await thanos_client.query("acm_managed_cluster_info")
            if result.get("status") != "success":
                logger.warning("acm_managed_cluster_info query failed")
                return None

            data = result.get("data", {}).get("result", [])
            if not data:
                logger.warning("No data from acm_managed_cluster_info")
                return None

            labels = data[0].get("metric", {})
            for candidate in CLUSTER_LABEL_CANDIDATES:
                if candidate in labels:
                    self.cluster_label = candidate
                    logger.info(f"Detected cluster label: {candidate}")
                    return candidate

            logger.warning("Could not detect cluster label from acm_managed_cluster_info")
            return None

        except Exception as e:
            logger.error(f"Error detecting cluster label: {e}")
            return None

    async def detect_node_label(self) -> Optional[str]:
        """Dynamically detect which label represents node name"""
        if self.node_label:
            return self.node_label

        try:
            result = await thanos_client.query("kube_node_info")
            if result.get("status") != "success":
                logger.warning("kube_node_info query failed")
                return None

            data = result.get("data", {}).get("result", [])
            if not data:
                logger.warning("No data from kube_node_info")
                return None

            labels = data[0].get("metric", {})
            for candidate in NODE_LABEL_CANDIDATES:
                if candidate in labels:
                    self.node_label = candidate
                    logger.info(f"Detected node label: {candidate}")
                    return candidate

            logger.warning("Could not detect node label from kube_node_info")
            return None

        except Exception as e:
            logger.error(f"Error detecting node label: {e}")
            return None

    async def discover_clusters(self) -> List[Dict]:
        """Discover all clusters from acm_managed_cluster_info"""
        if not self.cluster_label:
            await self.detect_cluster_label()

        if not self.cluster_label:
            logger.error("Cannot discover clusters without cluster_label")
            return []

        try:
            result = await thanos_client.query("acm_managed_cluster_info")
            if result.get("status") != "success":
                logger.error("Failed to query acm_managed_cluster_info")
                return []

            clusters = []
            data = result.get("data", {}).get("result", [])

            for series in data:
                metric = series.get("metric", {})
                cluster_name = metric.get(self.cluster_label, "unknown")

                if cluster_name not in self.discovered_clusters:
                    self.discovered_clusters.add(cluster_name)

                cluster_info = {
                    "cluster_name": cluster_name,
                    "cluster_id": metric.get(self.cluster_label, cluster_name),
                    "version": metric.get("version"),
                    "vendor": metric.get("vendor"),
                    "cloud": metric.get("cloud"),
                    "available": True
                }
                clusters.append(cluster_info)

            logger.info(f"Discovered {len(self.discovered_clusters)} clusters")
            return clusters

        except Exception as e:
            logger.error(f"Error discovering clusters: {e}")
            return []

    async def initialize(self):
        """Initialize discovery on startup"""
        logger.info("Starting cluster discovery...")
        await self.detect_cluster_label()
        await self.detect_node_label()
        await self.discover_clusters()
        logger.info(f"Discovery complete: {len(self.discovered_clusters)} clusters, "
                   f"cluster_label={self.cluster_label}, node_label={self.node_label}")


discovery = Discovery()
