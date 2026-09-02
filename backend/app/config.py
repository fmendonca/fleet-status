import logging
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    thanos_url: str = os.getenv("THANOS_URL", "http://localhost:9090")
    thanos_token: Optional[str] = os.getenv("THANOS_TOKEN")
    thanos_tls_verify: bool = os.getenv("THANOS_TLS_VERIFY", "true").lower() == "true"
    thanos_ca_file: Optional[str] = os.getenv("THANOS_CA_FILE")

    cache_ttl: int = int(os.getenv("CACHE_TTL", "30"))
    refresh_interval: int = int(os.getenv("REFRESH_INTERVAL", "30"))

    cpu_warning: float = float(os.getenv("CPU_WARNING", "70"))
    cpu_high: float = float(os.getenv("CPU_HIGH", "85"))
    cpu_critical: float = float(os.getenv("CPU_CRITICAL", "90"))

    memory_warning: float = float(os.getenv("MEMORY_WARNING", "75"))
    memory_high: float = float(os.getenv("MEMORY_HIGH", "85"))
    memory_critical: float = float(os.getenv("MEMORY_CRITICAL", "90"))

    high_cpu_window: str = os.getenv("HIGH_CPU_WINDOW", "5m")
    high_memory_window: str = os.getenv("HIGH_MEMORY_WINDOW", "5m")

    metrics_stale_threshold: str = os.getenv("METRICS_STALE_THRESHOLD", "5m")
    alert_ignore_list: str = os.getenv("ALERT_IGNORE_LIST", "Watchdog,InfoInhibitor")

    mock_mode: bool = os.getenv("MOCK_MODE", "false").lower() == "true"

    class Config:
        case_sensitive = False


settings = Settings()

if not settings.thanos_tls_verify:
    logger = logging.getLogger(__name__)
    logger.warning("THANOS_TLS_VERIFY=false: TLS verification disabled. Use only in development.")
