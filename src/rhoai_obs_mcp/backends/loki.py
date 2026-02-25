import logging
from typing import Literal

import httpx

from rhoai_obs_mcp.auth import AuthProvider
from rhoai_obs_mcp.config import Settings

logger = logging.getLogger(__name__)

Tenant = Literal["application", "infrastructure", "audit"]


_LOKI_NOT_CONFIGURED = "Loki is not configured. Set LOKI_URL to enable log queries."


class LokiBackend:
    """HTTP client for OpenShift LokiStack."""

    def __init__(self, settings: Settings, auth: AuthProvider) -> None:
        self._base_url = settings.loki_url or ""
        self._timeout = settings.request_timeout
        self._auth = auth
        self._available = settings.loki_enabled

    @property
    def available(self) -> bool:
        """Whether Loki is configured and available for queries."""
        return self._available

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._auth.get_headers(),
            timeout=self._timeout,
            verify=False,
        )

    def _tenant_path(self, tenant: Tenant) -> str:
        return f"/api/logs/v1/{tenant}/loki/api/v1"

    async def query_range(
        self,
        logql: str,
        tenant: Tenant = "application",
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
        direction: str = "backward",
    ) -> dict:
        """Execute a LogQL range query."""
        if not self._available:
            return {"status": "error", "error": _LOKI_NOT_CONFIGURED}

        params: dict = {"query": logql, "limit": limit, "direction": direction}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        try:
            async with self._client() as client:
                resp = await client.get(f"{self._tenant_path(tenant)}/query_range", params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Loki query failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def get_labels(self, tenant: Tenant = "application") -> list[str]:
        """List available labels for a tenant."""
        if not self._available:
            return []

        try:
            async with self._client() as client:
                resp = await client.get(f"{self._tenant_path(tenant)}/labels")
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Failed to list Loki labels: %s", exc)
            return []
