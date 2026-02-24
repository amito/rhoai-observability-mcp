import httpx
import pytest
import respx
from rhoai_obs_mcp.backends.alertmanager import AlertmanagerBackend


SAMPLE_ALERTS = [
    {
        "labels": {"alertname": "KubePodCrashLooping", "severity": "warning", "namespace": "vllm"},
        "annotations": {"summary": "Pod is crash looping"},
        "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
        "startsAt": "2024-01-01T00:00:00Z",
    },
    {
        "labels": {"alertname": "GPUHighUtilization", "severity": "critical", "namespace": "vllm"},
        "annotations": {"summary": "GPU utilization above 95%"},
        "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
        "startsAt": "2024-01-01T00:00:00Z",
    },
]


class TestAlertmanagerBackend:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_alerts(self, settings, auth):
        """Should fetch active alerts."""
        respx.get("https://alertmanager.test:9093/api/v2/alerts").mock(
            return_value=httpx.Response(200, json=SAMPLE_ALERTS)
        )

        backend = AlertmanagerBackend(settings, auth)
        result = await backend.get_alerts()
        assert len(result) == 2
        assert result[0]["labels"]["alertname"] == "KubePodCrashLooping"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_alerts_filtered_by_severity(self, settings, auth):
        """Should pass severity filter to API."""
        route = respx.get("https://alertmanager.test:9093/api/v2/alerts").mock(
            return_value=httpx.Response(200, json=[SAMPLE_ALERTS[1]])
        )

        backend = AlertmanagerBackend(settings, auth)
        await backend.get_alerts(severity="critical")
        assert "severity" in str(route.calls[0].request.url)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_alert_groups(self, settings, auth):
        """Should fetch alert groups."""
        respx.get("https://alertmanager.test:9093/api/v2/alerts/groups").mock(
            return_value=httpx.Response(
                200, json=[{"labels": {"namespace": "vllm"}, "alerts": SAMPLE_ALERTS}]
            )
        )

        backend = AlertmanagerBackend(settings, auth)
        result = await backend.get_alert_groups()
        assert len(result) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_error(self, settings, auth):
        """Should return empty list on connection error."""
        respx.get("https://alertmanager.test:9093/api/v2/alerts").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        backend = AlertmanagerBackend(settings, auth)
        result = await backend.get_alerts()
        assert result == []
