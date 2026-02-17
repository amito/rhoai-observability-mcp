# tests/unit/test_tools_alerts.py
import json
import pytest
from unittest.mock import AsyncMock
from rhoai_mcp.tools.alerts import register_alert_tools


SAMPLE_ALERTS = [
    {
        "labels": {"alertname": "KubePodCrashLooping", "severity": "warning"},
        "annotations": {"summary": "Pod is crash looping"},
        "status": {"state": "active"},
        "startsAt": "2024-01-01T00:00:00Z",
    },
]


class TestAlertTools:
    def setup_method(self):
        self.alertmanager = AsyncMock()
        self.tools = register_alert_tools(self.alertmanager)

    @pytest.mark.asyncio
    async def test_get_alerts(self):
        """Should return formatted alerts."""
        self.alertmanager.get_alerts.return_value = SAMPLE_ALERTS
        result = await self.tools["get_alerts"]()
        assert "KubePodCrashLooping" in result

    @pytest.mark.asyncio
    async def test_get_alerts_with_severity(self):
        """Should pass severity filter."""
        self.alertmanager.get_alerts.return_value = SAMPLE_ALERTS
        await self.tools["get_alerts"](severity="warning")
        self.alertmanager.get_alerts.assert_called_once_with(
            severity="warning", active_only=True, filter_expr=None
        )

    @pytest.mark.asyncio
    async def test_get_alert_groups(self):
        """Should return formatted alert groups."""
        self.alertmanager.get_alert_groups.return_value = [
            {"labels": {"namespace": "vllm"}, "alerts": SAMPLE_ALERTS}
        ]
        result = await self.tools["get_alert_groups"]()
        assert "vllm" in result
