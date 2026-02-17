import logging

import httpx

from rhoai_mcp.auth import AuthProvider
from rhoai_mcp.config import Settings

logger = logging.getLogger(__name__)


class PrometheusBackend:
    """HTTP client for Prometheus / ThanosQuerier."""

    def __init__(self, settings: Settings, auth: AuthProvider) -> None:
        self._base_url = settings.thanos_url or ""
        self._timeout = settings.request_timeout
        self._auth = auth

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._auth.get_headers(),
            timeout=self._timeout,
            verify=False,  # OpenShift routes use self-signed certs
        )

    async def query(self, promql: str, time: str | None = None) -> dict:
        """Execute an instant PromQL query."""
        params: dict = {"query": promql}
        if time:
            params["time"] = time
        try:
            async with self._client() as client:
                resp = await client.get("/api/v1/query", params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Prometheus query failed: %s", exc)
            return {"status": "error", "error": str(exc), "errorType": "connection"}

    async def query_range(
        self, promql: str, start: str, end: str, step: str = "60s"
    ) -> dict:
        """Execute a range PromQL query."""
        params = {"query": promql, "start": start, "end": end, "step": step}
        try:
            async with self._client() as client:
                resp = await client.get("/api/v1/query_range", params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Prometheus range query failed: %s", exc)
            return {"status": "error", "error": str(exc), "errorType": "connection"}

    async def list_metrics(self, match: str | None = None) -> list[str]:
        """List available metric names."""
        try:
            async with self._client() as client:
                params = {}
                if match:
                    params["match[]"] = match
                resp = await client.get("/api/v1/label/__name__/values", params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Failed to list metrics: %s", exc)
            return []
