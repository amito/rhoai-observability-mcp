# Contributing

## Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/rhoai-observability-mcp.git
cd rhoai-observability-mcp

# Install with dev dependencies
uv pip install -e ".[dev]"

# Verify setup
uv run pytest -q
uv run ruff check .
```

## Code Standards

- **Python 3.11+** -- use modern syntax (`str | None`, not `Optional[str]`)
- **Type hints** on all public functions
- **Line length** 100 characters (configured in `pyproject.toml`)
- **Formatter/linter:** [ruff](https://docs.astral.sh/ruff/)

### Linting

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

## Project Structure

```
src/rhoai_obs_mcp/
  __init__.py
  auth.py                # Token management (service account + bearer token)
  config.py              # Settings via pydantic-settings (env vars / .env)
  server.py              # FastMCP server creation and tool registration
  backends/
    __init__.py
    alertmanager.py      # Alertmanager HTTP client
    grafana.py           # Grafana HTTP client
    loki.py              # LokiStack HTTP client
    openshift.py         # Kubernetes API client
    prometheus.py        # Thanos/Prometheus HTTP client
  tools/
    __init__.py
    alerts.py            # get_alerts, get_alert_groups
    cluster.py           # get_pods, get_events, get_node_status, describe_resource, get_inference_services
    dashboards.py        # list_dashboards, get_dashboard_panels
    investigate.py       # investigate_latency, investigate_gpu, investigate_errors
    logs.py              # query_logs, get_pod_logs
    metrics.py           # query_prometheus, get_vllm_metrics, list_metrics
tests/
  unit/
    conftest.py          # Shared fixtures (settings, auth)
    test_*.py            # One test file per module
  smoke_test.py          # Live cluster integration test
```

## Adding a New Tool

### 1. Create or extend a backend client

If your tool talks to a new service, add a backend in `src/rhoai_obs_mcp/backends/`:

```python
# backends/myservice.py
from rhoai_obs_mcp.auth import AuthProvider
from rhoai_obs_mcp.config import Settings

class MyServiceBackend:
    def __init__(self, settings: Settings, auth: AuthProvider):
        self._settings = settings
        self._auth = auth

    async def fetch_data(self, param: str) -> dict:
        # Use httpx.AsyncClient for HTTP calls
        ...
```

### 2. Create a tool registration function

Add a tool module in `src/rhoai_obs_mcp/tools/`:

```python
# tools/mytools.py
from rhoai_obs_mcp.backends.myservice import MyServiceBackend

def register_my_tools(backend: MyServiceBackend) -> dict:
    async def my_tool(param: str) -> str:
        """Tool description shown to the AI assistant.

        Args:
            param: Description of this parameter
        """
        result = await backend.fetch_data(param)
        return format_result(result)

    return {"my_tool": my_tool}
```

### 3. Register in `server.py`

Add the backend initialization and tool registration in `create_server()`:

```python
myservice = MyServiceBackend(settings, auth)
# ...
tool_groups = [
    # existing groups...
    register_my_tools(myservice),
]
```

### 4. Write tests

- Add unit tests in `tests/unit/test_tools_mytools.py`
- Mock all HTTP calls with `respx`
- See [TESTING.md](TESTING.md) for patterns

## Submitting Changes

1. Create a feature branch: `git checkout -b my-feature`
2. Write tests first, then implement
3. Run the full test suite: `uv run pytest -q`
4. Run the linter: `uv run ruff check . && uv run ruff format --check .`
5. Submit a pull request with a clear description of the change

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
