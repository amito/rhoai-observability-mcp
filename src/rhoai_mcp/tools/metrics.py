import json
import re

from rhoai_mcp.backends.prometheus import PrometheusBackend

# Key vLLM metrics with human-readable descriptions
VLLM_METRICS = {
    "ttft": ("vllm:time_to_first_token_seconds", "Time to First Token (TTFT)"),
    "tpot": ("vllm:time_per_output_token_seconds", "Time Per Output Token (TPOT)"),
    "e2e": ("vllm:e2e_request_latency_seconds", "End-to-End Latency"),
    "cache": ("vllm:gpu_cache_usage_perc", "GPU KV Cache Usage"),
    "throughput": ("vllm:generation_tokens_total", "Generation Throughput (tokens/sec)"),
    "queue": ("vllm:num_requests_waiting", "Requests Waiting in Queue"),
    "running": ("vllm:num_requests_running", "Requests Currently Running"),
}


def register_metrics_tools(prometheus: PrometheusBackend) -> dict:
    """Create metrics tool functions bound to the given backend."""

    async def query_prometheus(query: str, time: str | None = None) -> str:
        """Execute a raw PromQL query against ThanosQuerier.

        Args:
            query: PromQL expression (e.g., 'vllm:num_requests_running')
            time: Optional evaluation timestamp (RFC3339 or Unix)
        """
        result = await prometheus.query(query, time=time)
        return json.dumps(result, indent=2, default=str)

    async def get_vllm_metrics(
        model_name: str,
        metrics: str = "ttft,tpot,e2e,cache,queue,running",
    ) -> str:
        """Get a summary of key vLLM metrics for a specific model.

        Args:
            model_name: The model name label in vLLM metrics
            metrics: Comma-separated list of: ttft, tpot, e2e, cache, throughput, queue, running
        """
        requested = [m.strip() for m in metrics.split(",")]
        lines = [f"## vLLM Metrics for model: {model_name}\n"]

        for key in requested:
            if key not in VLLM_METRICS:
                lines.append(f"- **{key}**: Unknown metric key")
                continue

            metric_name, description = VLLM_METRICS[key]

            # For rate-based metrics, wrap in rate()
            if key == "throughput":
                promql = f'rate({metric_name}{{model_name="{model_name}"}}[5m])'
            elif key in ("cache", "queue", "running"):
                promql = f'{metric_name}{{model_name="{model_name}"}}'
            else:
                # Histograms: get p50, p95, p99
                promql = f'histogram_quantile(0.95, rate({metric_name}_bucket{{model_name="{model_name}"}}[5m]))'

            result = await prometheus.query(promql)
            if result.get("status") == "success" and result["data"].get("result"):
                value = result["data"]["result"][0]["value"][1]
                lines.append(f"- **{description}**: {value}")
            else:
                lines.append(f"- **{description}**: No data available")

        return "\n".join(lines)

    async def list_metrics(filter: str = "") -> str:
        """List available Prometheus metric names, optionally filtered.

        Args:
            filter: Regex pattern to filter metric names (e.g., 'vllm' to show only vLLM metrics)
        """
        all_metrics = await prometheus.list_metrics()
        if filter:
            pattern = re.compile(filter, re.IGNORECASE)
            filtered = [m for m in all_metrics if pattern.search(m)]
        else:
            filtered = all_metrics

        if not filtered:
            return (
                f"No metrics found matching filter: '{filter}'"
                if filter
                else "No metrics available"
            )

        return "\n".join(sorted(filtered))

    return {
        "query_prometheus": query_prometheus,
        "get_vllm_metrics": get_vllm_metrics,
        "list_metrics": list_metrics,
    }
