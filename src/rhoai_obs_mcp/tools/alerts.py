import json

from rhoai_obs_mcp.backends.alertmanager import AlertmanagerBackend


def register_alert_tools(alertmanager: AlertmanagerBackend) -> dict:
    """Create alert tool functions bound to the given backend."""

    async def get_alerts(
        severity: str | None = None,
        active_only: bool = True,
        filter: str | None = None,
    ) -> str:
        """Get active alerts from Alertmanager.

        Args:
            severity: Filter by severity level (e.g., 'critical', 'warning')
            active_only: Only return active (non-silenced) alerts
            filter: Label matcher expression (e.g., 'namespace="vllm"')
        """
        alerts = await alertmanager.get_alerts(
            severity=severity, active_only=active_only, filter_expr=filter
        )

        if not alerts:
            return "No active alerts found."

        lines = [f"## Active Alerts ({len(alerts)} total)\n"]
        for alert in alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            lines.append(f"### {labels.get('alertname', 'Unknown')}")
            lines.append(f"- **Severity:** {labels.get('severity', 'unknown')}")
            lines.append(f"- **Summary:** {annotations.get('summary', 'N/A')}")
            if annotations.get("description"):
                lines.append(f"- **Description:** {annotations['description']}")
            lines.append(f"- **Started:** {alert.get('startsAt', 'N/A')}")
            extra_labels = {k: v for k, v in labels.items() if k not in ("alertname", "severity")}
            if extra_labels:
                lines.append(f"- **Labels:** {json.dumps(extra_labels)}")
            lines.append("")

        return "\n".join(lines)

    async def get_alert_groups() -> str:
        """Get alerts grouped by their routing labels."""
        groups = await alertmanager.get_alert_groups()

        if not groups:
            return "No alert groups found."

        lines = ["## Alert Groups\n"]
        for group in groups:
            group_labels = group.get("labels", {})
            alerts = group.get("alerts", [])
            lines.append(f"### Group: {json.dumps(group_labels)}")
            lines.append(f"- **Alert count:** {len(alerts)}")
            for alert in alerts:
                name = alert.get("labels", {}).get("alertname", "Unknown")
                state = alert.get("status", {}).get("state", "unknown")
                lines.append(f"  - {name} ({state})")
            lines.append("")

        return "\n".join(lines)

    return {
        "get_alerts": get_alerts,
        "get_alert_groups": get_alert_groups,
    }
