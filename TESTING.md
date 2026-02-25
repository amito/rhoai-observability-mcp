# Testing

## Running Tests

### All unit tests

```bash
uv run pytest -q
```

### With coverage

```bash
uv run pytest --cov=src --cov-fail-under=80
```

### Specific test file

```bash
uv run pytest tests/unit/test_tools_metrics.py -q
```

### Specific test function

```bash
uv run pytest tests/unit/test_tools_metrics.py::test_query_prometheus_success -q
```

## Test Structure

```
tests/
  __init__.py
  smoke_test.py              # Live cluster smoke tests
  unit/
    __init__.py
    conftest.py              # Shared fixtures (settings, auth)
    test_auth.py
    test_config.py
    test_server.py
    test_backends_alertmanager.py
    test_backends_grafana.py
    test_backends_loki.py
    test_backends_openshift.py
    test_backends_prometheus.py
    test_tools_alerts.py
    test_tools_cluster.py
    test_tools_dashboards.py
    test_tools_investigate.py
    test_tools_logs.py
    test_tools_metrics.py
```

### Shared Fixtures (`conftest.py`)

The `conftest.py` provides two fixtures used across all unit tests:

- **`settings`** -- A `Settings` instance with test URLs and a dummy token
- **`auth`** -- An `AuthProvider` bound to the test settings

## Smoke Tests (Live Cluster)

The smoke test runs against a real OpenShift cluster to verify end-to-end connectivity.

### Prerequisites

- `oc` CLI authenticated to a cluster, **or** environment variables set

### Running

```bash
# With auto-detection (requires oc login)
uv run python tests/smoke_test.py

# With explicit URLs
THANOS_URL=https://thanos-querier.apps.mycluster.example.com \
ALERTMANAGER_URL=https://alertmanager-main.apps.mycluster.example.com \
OPENSHIFT_TOKEN=$(oc whoami -t) \
uv run python tests/smoke_test.py
```

The smoke test covers:

1. Prometheus instant query (`up`)
2. Metric listing (DCGM filter)
3. GPU utilization query
4. Alertmanager active alerts
5. Pod listing
6. InferenceService listing
7. Node status and GPU info
8. Kubernetes events

## Writing New Tests

### Pattern: Backend tests with `respx`

All HTTP backends use `httpx.AsyncClient`. Mock HTTP calls with `respx`:

```python
import respx
from httpx import Response

@respx.mock
async def test_my_backend_method(settings, auth):
    backend = MyBackend(settings, auth)

    respx.get("https://backend.test/api/endpoint").mock(
        return_value=Response(200, json={"status": "success", "data": {...}})
    )

    result = await backend.my_method()
    assert result["status"] == "success"
```

### Pattern: Tool tests

Tool tests create the backend, register tools, then call the tool functions directly:

```python
@respx.mock
async def test_my_tool(settings, auth):
    backend = MyBackend(settings, auth)
    tools = register_my_tools(backend)

    respx.get("https://backend.test/api/query").mock(
        return_value=Response(200, json={...})
    )

    result = await tools["my_tool_name"](arg1="value")
    assert "expected text" in result
```

### Key conventions

- All async tests run automatically via `asyncio_mode = "auto"` in `pyproject.toml`
- Mock all HTTP calls -- unit tests must not hit real services
- Use the `settings` and `auth` fixtures from `conftest.py`
- Test files follow the naming pattern `test_<module>.py`
