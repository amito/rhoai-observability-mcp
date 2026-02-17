# RHOAI Observability MCP Server — Design Document

**Date:** 2026-02-17
**Status:** Approved

## Purpose

An MCP server that bridges Red Hat OpenShift AI's observability stack (Prometheus/ThanosQuerier, Grafana, Loki, Alertmanager) and the OpenShift cluster API, enabling AI-driven natural language querying and root cause analysis for LLM deployments — specifically vLLM inference workloads.

**Audience:** Demo-ready for a Red Hat Summit lightning talk, production-capable for platform engineers and MLOps teams.

## Architecture

**Approach: Flat Tool Set** — A single Python MCP server exposing individual tools per backend, plus composite investigation tools for multi-source correlation.

```
LLM Client (Claude, etc.)
  │
  └─ stdio/SSE ──► FastMCP Server
                      │
                      ├── tools/metrics.py     ──► backends/prometheus.py   ──► ThanosQuerier
                      ├── tools/alerts.py      ──► backends/alertmanager.py ──► Alertmanager v2
                      ├── tools/logs.py        ──► backends/loki.py         ──► LokiStack
                      ├── tools/cluster.py     ──► backends/openshift.py    ──► Kubernetes API
                      ├── tools/dashboards.py  ──► backends/grafana.py      ──► Grafana API
                      └── tools/investigate.py ──► (multiple backends concurrently)
```

## Tool Inventory (17 tools)

### Metrics (Prometheus/ThanosQuerier)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `query_prometheus` | `query` (PromQL), `time_range` (default 5m), `step` | Time-series data or instant vector |
| `get_vllm_metrics` | `model_name`, `metrics` (list: ttft, tpot, e2e, cache, throughput, queue) | Formatted vLLM metrics summary |
| `list_metrics` | `filter` (regex on metric name) | Available metric names matching filter |

### Alerts (Alertmanager v2)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_alerts` | `severity` (optional), `active_only` (bool), `filter` (label matcher) | Active alerts with labels, annotations, state |
| `get_alert_groups` | none | Grouped alerts by routing rules |

### Logs (Loki)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `query_logs` | `logql` (query), `tenant` (application/infrastructure/audit), `time_range`, `limit` | Log entries matching query |
| `get_pod_logs` | `namespace`, `pod_name`, `container` (optional), `time_range`, `filter` | Convenience wrapper building LogQL from params |

### Cluster (Kubernetes API)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_pods` | `namespace`, `label_selector` (optional), `field_selector` (optional) | Pod list with status, restarts, age |
| `get_events` | `namespace`, `resource_name` (optional), `reason` (optional) | Kubernetes events |
| `get_node_status` | `node_name` (optional) | Node conditions, capacity, GPU allocation |
| `describe_resource` | `resource_type`, `name`, `namespace` | Full resource description |
| `get_inference_services` | `namespace` (optional) | KServe InferenceService list with status |

### Dashboards (Grafana)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `list_dashboards` | `tag` (optional), `search` (optional) | Available Grafana dashboards |
| `get_dashboard_panels` | `dashboard_uid` | Panel list with queries, types |

### Composite Investigation

| Tool | Parameters | Returns |
|------|-----------|---------|
| `investigate_latency` | `model_name`, `time_range` | TTFT/TPOT/E2E + queue depth + error logs + alerts |
| `investigate_gpu` | `time_range`, `namespace` (optional) | GPU util (DCGM) + KV cache + running/waiting + pod status |
| `investigate_errors` | `namespace`, `time_range` | Error logs + firing alerts + pod restarts + metric anomalies |

## Authentication

Auto-detects environment:

- **In-cluster:** ServiceAccount token from `/var/run/secrets/kubernetes.io/serviceaccount/token`. Backend services accessed via internal cluster DNS.
- **External:** Kubeconfig token (same as `oc whoami -t`). Backend services accessed via OpenShift Routes (auto-detected or configured).

## Configuration

Environment variables with auto-detection defaults:

```
THANOS_URL          # Auto-detected from cluster routes/services
ALERTMANAGER_URL    # Auto-detected
LOKI_URL            # Auto-detected
GRAFANA_URL         # Auto-detected
OPENSHIFT_TOKEN     # Auto-detected from kubeconfig/SA
DEFAULT_TIME_RANGE  # Default: 5m
LOG_LEVEL           # Default: INFO
```

Startup validates connectivity to each backend and logs availability.

## Project Structure

```
rhoai-observability-mcp/
├── pyproject.toml
├── src/
│   └── rhoai_mcp/
│       ├── __init__.py
│       ├── server.py              # FastMCP server, tool registration
│       ├── config.py              # Pydantic BaseSettings, auto-detection
│       ├── auth.py                # Token management (SA vs kubeconfig)
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── prometheus.py      # ThanosQuerier HTTP client
│       │   ├── alertmanager.py    # Alertmanager v2 API client
│       │   ├── loki.py            # LokiStack HTTP client
│       │   ├── grafana.py         # Grafana HTTP API client
│       │   └── openshift.py       # Kubernetes Python client wrapper
│       └── tools/
│           ├── __init__.py
│           ├── metrics.py
│           ├── alerts.py
│           ├── logs.py
│           ├── cluster.py
│           ├── dashboards.py
│           └── investigate.py
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    └── plans/
```

## Dependencies

```toml
[project]
name = "rhoai-observability-mcp"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
    "pydantic>=2.0",
    "kubernetes>=31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "respx>=0.22",
    "ruff>=0.8",
]
```

## Key vLLM Metrics

The server targets these vLLM Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `vllm:time_to_first_token_seconds` | Histogram | TTFT |
| `vllm:time_per_output_token_seconds` | Histogram | TPOT (inter-token latency) |
| `vllm:e2e_request_latency_seconds` | Histogram | End-to-end request latency |
| `vllm:num_requests_running` | Gauge | Requests in execution |
| `vllm:num_requests_waiting` | Gauge | Requests queued |
| `vllm:gpu_cache_usage_perc` | Gauge | GPU KV cache utilization |
| `vllm:prompt_tokens_total` | Counter | Total prompt tokens |
| `vllm:generation_tokens_total` | Counter | Total generation tokens |
| `vllm:request_success_total` | Counter | Completed requests |
| `vllm:request_queue_time_seconds` | Histogram | Queue wait time |

GPU utilization comes from DCGM Exporter (`DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`).

## Backend API Details

### ThanosQuerier
- Endpoints: `/api/v1/query`, `/api/v1/query_range`, `/api/v1/labels`, `/api/v1/series`
- Auth: Bearer token, `cluster-monitoring-view` role required
- Internal: `thanos-querier.openshift-monitoring.svc:9091`

### Alertmanager v2
- Endpoints: `/api/v2/alerts`, `/api/v2/alerts/groups`, `/api/v2/silences`
- Filtering: `?filter=alertname="X"&active=true&silenced=false`
- Internal: `alertmanager-main.openshift-monitoring.svc:9093`

### LokiStack
- URL pattern: `/api/logs/v1/{tenant}/loki/api/v1/query_range`
- Tenants: `application`, `infrastructure`, `audit`
- LogQL for filtering: `{kubernetes_namespace_name="ns"} |= "error"`
- Internal: `lokistack-dev-gateway-http.openshift-logging.svc:8080`

### Grafana
- Endpoints: `/api/search` (dashboards), `/api/dashboards/uid/{uid}`
- Auth: Bearer token or API key

### Kubernetes API
- Via `kubernetes` Python client
- Resources: Pods, Events, Nodes, custom resources (InferenceService)

## Error Handling

- Backend unreachable → structured error in tool response (not exception)
- Auth expired → attempt refresh, return re-auth message if failed
- Empty results → explicit "no data found" message
- Timeouts → 30s per backend, composite tools use per-backend timeouts

## Composite Tool Concurrency

Investigation tools query backends concurrently via `asyncio.gather` so one slow backend doesn't block others.

## Testing

- **Unit tests:** Every tool tested with mocked HTTP responses (respx) and mocked Kubernetes client
- **Integration tests:** Optional, marked `@pytest.mark.integration`, run against real cluster
- **Demo validation:** Manual test with MCP client in stdio mode
