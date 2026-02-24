import logging

import httpx

from rhoai_obs_mcp.auth import AuthProvider
from rhoai_obs_mcp.config import Settings

logger = logging.getLogger(__name__)


class AlertmanagerBackend:
    """HTTP client for Alertmanager v2 API."""

    def __init__(self, settings: Settings, auth: AuthProvider) -> None:
        self._base_url = settings.alertmanager_url or ""
        self._timeout = settings.request_timeout
        self._auth = auth

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._auth.get_headers(),
            timeout=self._timeout,
            verify=False,
        )

    async def get_alerts(
        self,
        severity: str | None = None,
        active_only: bool = True,
        filter_expr: str | None = None,
    ) -> list[dict]:
        """Fetch alerts from Alertmanager."""
        params: dict = {
            "active": str(active_only).lower(),
            "silenced": "false",
            "inhibited": "false",
        }
        filters = []
        if severity:
            filters.append(f'severity="{severity}"')
        if filter_expr:
            filters.append(filter_expr)
        if filters:
            params["filter"] = filters

        try:
            async with self._client() as client:
                resp = await client.get("/api/v2/alerts", params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Alertmanager query failed: %s", exc)
            return []

    async def get_alert_groups(self) -> list[dict]:
        """Fetch alert groups."""
        try:
            async with self._client() as client:
                resp = await client.get("/api/v2/alerts/groups")
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.error("Alertmanager groups query failed: %s", exc)
            return []
