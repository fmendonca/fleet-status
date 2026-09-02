import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)


class ThanosClient:
    def __init__(self):
        self.base_url = settings.thanos_url.rstrip("/")
        self.token = settings.thanos_token
        self.tls_verify = settings.thanos_tls_verify if settings.thanos_tls_verify else False
        self.ca_file = settings.thanos_ca_file

        self.timeout = 30
        self.retry_count = 3
        self.retry_backoff = 2

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def query(self, promql: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/query"
        params = {"query": promql}
        headers = self._get_headers()

        for attempt in range(self.retry_count):
            try:
                async with httpx.AsyncClient(verify=self.tls_verify, timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                if attempt < self.retry_count - 1:
                    wait = self.retry_backoff ** attempt
                    logger.warning(f"Query failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Query failed after {self.retry_count} attempts: {e}")
                    return {"status": "error", "error": str(e)}

    async def query_range(self, promql: str, start: datetime, end: datetime, step: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step
        }
        headers = self._get_headers()

        for attempt in range(self.retry_count):
            try:
                async with httpx.AsyncClient(verify=self.tls_verify, timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                if attempt < self.retry_count - 1:
                    wait = self.retry_backoff ** attempt
                    logger.warning(f"Query_range failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"Query_range failed after {self.retry_count} attempts: {e}")
                    return {"status": "error", "error": str(e)}

    async def series(self, match: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/series"
        params = {"match[]": match}
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(verify=self.tls_verify, timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Series query failed: {e}")
            return {"status": "error", "error": str(e)}

    async def labels(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/labels"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(verify=self.tls_verify, timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Labels query failed: {e}")
            return {"status": "error", "error": str(e)}

    async def label_values(self, label: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/label/{label}/values"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(verify=self.tls_verify, timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Label values query failed: {e}")
            return {"status": "error", "error": str(e)}

    async def is_available(self) -> bool:
        try:
            result = await self.labels()
            return result.get("status") == "success"
        except Exception:
            return False


thanos_client = ThanosClient()
