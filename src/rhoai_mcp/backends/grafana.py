import logging

import httpx

from rhoai_mcp.auth import AuthProvider
from rhoai_mcp.config import Settings

logger = logging.getLogger(__name__)


class GrafanaBackend:
    """HTTP client for Grafana API."""

    def __init__(self, settings: Settings, auth: AuthProvider) -> None:
        self._base_url = settings.grafana_url or ""
        self._timeout = settings.request_timeout
        self._auth = auth

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._auth.get_headers(),
            timeout=self._timeout,
            verify=False,
        )

    async def search_dashboards(
        self, query: str | None = None, tag: str | None = None
    ) -> list[dict]:
        """Search for Grafana dashboards."""
        params: dict = {"type": "dash-db"}
        if query:
            params["query"] = query
        if tag:
            params["tag"] = tag

        try:
            async with self._client() as client:
                resp = await client.get("/api/search", params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Grafana search failed: %s", exc)
            return []

    async def get_dashboard(self, uid: str) -> dict:
        """Fetch a dashboard by UID."""
        try:
            async with self._client() as client:
                resp = await client.get(f"/api/dashboards/uid/{uid}")
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Grafana dashboard fetch failed: %s", exc)
            return {"error": str(exc)}
