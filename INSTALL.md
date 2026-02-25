# Installation

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- Access to an **OpenShift cluster** with RHOAI deployed (for live usage)
- `oc` CLI authenticated to the cluster (or a bearer token)

## Install

```bash
git clone https://github.com/your-org/rhoai-observability-mcp.git
cd rhoai-observability-mcp
uv pip install -e ".[dev]"
```

## Configuration

All settings are configured via environment variables or a `.env` file in the project root.

| Variable | Description | Default |
|----------|-------------|---------|
| `THANOS_URL` | ThanosQuerier URL for Prometheus queries | Auto-detected via OpenShift route |
| `ALERTMANAGER_URL` | Alertmanager URL | Auto-detected via OpenShift route |
| `LOKI_URL` | LokiStack gateway URL | Auto-detected via OpenShift route |
| `GRAFANA_URL` | Grafana URL | Auto-detected via OpenShift route |
| `OPENSHIFT_TOKEN` | Bearer token override | Auto-detected from service account or `oc whoami -t` |
| `DEFAULT_TIME_RANGE` | Default PromQL/LogQL time range | `5m` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `REQUEST_TIMEOUT` | HTTP request timeout in seconds | `30.0` |

### Auto-Detection

When running **inside** an OpenShift cluster (as a pod), the server automatically:

- Reads the service account token from `/var/run/secrets/kubernetes.io/serviceaccount/token`
- Uses in-cluster service URLs for backends

When running **externally**, set the URL and token environment variables, or ensure `oc` is authenticated so the smoke tests can auto-discover routes.

### Example `.env` File

```env
THANOS_URL=https://thanos-querier-openshift-monitoring.apps.mycluster.example.com
ALERTMANAGER_URL=https://alertmanager-main-openshift-monitoring.apps.mycluster.example.com
LOKI_URL=https://logging-loki-openshift-logging.apps.mycluster.example.com
GRAFANA_URL=https://grafana-open-cluster-management-observability.apps.mycluster.example.com
OPENSHIFT_TOKEN=sha256~xxxxxxxxxxxxxxxxxxxx
LOG_LEVEL=DEBUG
```

## Running the Server

### Direct execution

```bash
python -m rhoai_obs_mcp.server
```

This starts the MCP server on stdio transport.

### Via MCP CLI

```bash
mcp run src/rhoai_obs_mcp/server.py
```

### Programmatic

```python
from rhoai_obs_mcp.server import create_server

mcp = create_server()
mcp.run(transport="stdio")
```

You can also pass configuration overrides:

```python
mcp = create_server(settings_override={
    "thanos_url": "https://thanos.example.com",
    "openshift_token": "my-token",
})
```

## Claude Desktop Integration

Add the following to your Claude Desktop MCP configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rhoai-observability": {
      "command": "python",
      "args": ["-m", "rhoai_obs_mcp.server"],
      "cwd": "/path/to/rhoai-observability-mcp",
      "env": {
        "THANOS_URL": "https://thanos-querier.apps.mycluster.example.com",
        "ALERTMANAGER_URL": "https://alertmanager-main.apps.mycluster.example.com",
        "OPENSHIFT_TOKEN": "sha256~xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

## Claude Code Integration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "rhoai-observability": {
      "command": "python",
      "args": ["-m", "rhoai_obs_mcp.server"],
      "cwd": "/path/to/rhoai-observability-mcp",
      "env": {
        "THANOS_URL": "https://thanos-querier.apps.mycluster.example.com",
        "OPENSHIFT_TOKEN": "sha256~xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```
