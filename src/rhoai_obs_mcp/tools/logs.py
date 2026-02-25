from typing import Literal

from rhoai_obs_mcp.backends.loki import LokiBackend


def _format_log_response(data: dict) -> str:
    """Format Loki response into readable text."""
    if data.get("status") == "error":
        return f"Error querying logs: {data.get('error', 'Unknown error')}"

    results = data.get("data", {}).get("result", [])
    if not results:
        return "No log entries found for the given query."

    lines = []
    for stream in results:
        labels = stream.get("stream", {})
        pod = labels.get("kubernetes_pod_name", "unknown")
        lines.append(f"## Pod: {pod}")
        for timestamp, message in stream.get("values", []):
            lines.append(f"  {message}")
        lines.append("")

    return "\n".join(lines)


def register_log_tools(loki: LokiBackend) -> dict:
    """Create log tool functions bound to the given backend."""

    async def query_logs(
        logql: str,
        tenant: Literal["application", "infrastructure", "audit"] = "application",
        time_range: str = "1h",
        limit: int = 100,
    ) -> str:
        """Execute a LogQL query against OpenShift LokiStack.

        Args:
            logql: LogQL query (e.g., '{kubernetes_namespace_name="vllm"} |= "error"')
            tenant: Log tenant: 'application', 'infrastructure', or 'audit'
            time_range: How far back to search (e.g., '1h', '30m')
            limit: Maximum number of log entries to return
        """
        result = await loki.query_range(logql, tenant=tenant, limit=limit)
        return _format_log_response(result)

    async def get_pod_logs(
        namespace: str,
        pod_name: str,
        container: str | None = None,
        time_range: str = "1h",
        filter: str | None = None,
    ) -> str:
        """Get logs for a specific pod by building a LogQL query.

        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            container: Container name (optional, for multi-container pods)
            time_range: How far back to search
            filter: Text filter to apply (e.g., 'error', 'timeout')
        """
        logql = f'{{kubernetes_namespace_name="{namespace}", kubernetes_pod_name="{pod_name}"}}'
        if container:
            logql = (
                f'{{kubernetes_namespace_name="{namespace}", '
                f'kubernetes_pod_name="{pod_name}", '
                f'kubernetes_container_name="{container}"}}'
            )
        if filter:
            logql += f' |= "{filter}"'

        result = await loki.query_range(logql, tenant="application")
        return _format_log_response(result)

    return {
        "query_logs": query_logs,
        "get_pod_logs": get_pod_logs,
    }
