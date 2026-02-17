from rhoai_mcp.backends.grafana import GrafanaBackend


def register_dashboard_tools(grafana: GrafanaBackend) -> dict:
    """Create dashboard tool functions bound to the given backend."""

    async def list_dashboards(tag: str | None = None, search: str | None = None) -> str:
        """List available Grafana dashboards.

        Args:
            tag: Filter by tag (e.g., 'vllm', 'gpu')
            search: Search dashboards by title
        """
        dashboards = await grafana.search_dashboards(query=search, tag=tag)

        if not dashboards:
            return "No dashboards found."

        lines = ["## Grafana Dashboards\n"]
        for dash in dashboards:
            tags = ", ".join(dash.get("tags", []))
            tag_str = f" [{tags}]" if tags else ""
            lines.append(f"- **{dash['title']}** (uid: `{dash['uid']}`){tag_str}")

        return "\n".join(lines)

    async def get_dashboard_panels(dashboard_uid: str) -> str:
        """Get the panels and their queries from a Grafana dashboard.

        Args:
            dashboard_uid: The dashboard UID (from list_dashboards)
        """
        data = await grafana.get_dashboard(dashboard_uid)

        if "error" in data:
            return f"Error fetching dashboard: {data['error']}"

        dashboard = data.get("dashboard", {})
        panels = dashboard.get("panels", [])

        if not panels:
            return f"Dashboard '{dashboard.get('title', dashboard_uid)}' has no panels."

        lines = [f"## Dashboard: {dashboard.get('title', 'Unknown')}\n"]
        for panel in panels:
            lines.append(f"### {panel.get('title', 'Untitled')} ({panel.get('type', 'unknown')})")
            targets = panel.get("targets", [])
            for target in targets:
                expr = target.get("expr", "")
                if expr:
                    lines.append(f"  - Query: `{expr}`")
            lines.append("")

        return "\n".join(lines)

    return {
        "list_dashboards": list_dashboards,
        "get_dashboard_panels": get_dashboard_panels,
    }
