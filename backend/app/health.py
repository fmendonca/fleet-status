import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class HealthCalculator:
    """Calculate cluster health based on metrics"""

    @staticmethod
    def determine_cluster_status(
        available: bool,
        nodes_not_ready: int,
        nodes_total: int,
        critical_alerts: int,
        warning_alerts: int,
        cpu_avg: float,
        cpu_peak: float,
        memory_avg: float,
        memory_peak: float,
        metrics_age_seconds: int,
        has_metrics: bool
    ) -> str:
        """Determine overall cluster status"""

        if not has_metrics or metrics_age_seconds is None:
            return "NO_DATA"

        if not available:
            return "CRITICAL"

        if nodes_not_ready > 0:
            return "CRITICAL"

        if critical_alerts > 0:
            return "CRITICAL"

        if cpu_peak >= settings.cpu_critical:
            return "CRITICAL"

        if memory_peak >= settings.memory_critical:
            return "CRITICAL"

        if nodes_total > 0 and (nodes_not_ready / nodes_total) > 0.1:
            return "CRITICAL"

        has_warning = False

        if nodes_total > 0 and (nodes_not_ready / nodes_total) > 0:
            has_warning = True

        if warning_alerts > 0:
            has_warning = True

        if cpu_avg >= settings.cpu_warning or cpu_peak >= settings.cpu_high:
            has_warning = True

        if memory_avg >= settings.memory_warning or memory_peak >= settings.memory_high:
            has_warning = True

        if has_warning:
            return "WARNING"

        return "HEALTHY"

    @staticmethod
    def classify_cpu(cpu_value: float) -> str:
        """Classify CPU level"""
        if cpu_value >= settings.cpu_critical:
            return "CRITICAL"
        elif cpu_value >= settings.cpu_high:
            return "HIGH"
        elif cpu_value >= settings.cpu_warning:
            return "WARNING"
        else:
            return "NORMAL"

    @staticmethod
    def classify_memory(memory_value: float) -> str:
        """Classify memory level"""
        if memory_value >= settings.memory_critical:
            return "CRITICAL"
        elif memory_value >= settings.memory_high:
            return "HIGH"
        elif memory_value >= settings.memory_warning:
            return "WARNING"
        else:
            return "NORMAL"


health_calc = HealthCalculator()
