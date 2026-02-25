# Design: OpenShift Deployment for RHOAI Observability MCP

**Date:** 2026-02-25
**Status:** Approved

## Context

The RHOAI Observability MCP server needs to be deployable as a containerized workload on OpenShift. This requires a container image, OpenShift manifests, and build/deploy tooling. The server already supports in-cluster auth (SA token auto-detection) and env-var-based configuration.

## Decisions

- **Transport:** SSE (Server-Sent Events) over HTTP — the standard MCP remote transport, natively supported by FastMCP.
- **Approach:** Plain Kubernetes/OpenShift YAML manifests in `deploy/` with a Makefile. No Helm or OpenShift Templates.
- **RBAC:** Scoped ClusterRole with read-only access to exactly the resources the tools query.
- **Registry:** Quay.io (`quay.io/rh-ee-amoren/rhoai-observability-mcp`).
- **Base image:** UBI9 Python 3.12 (`registry.access.redhat.com/ubi9/python-312`) for OpenShift compatibility.

## Container Image

Multi-stage build using a Containerfile:

- **Build stage:** UBI9 Python 3.12, install `uv` from official image, copy `pyproject.toml` + `uv.lock` + `src/`, run `uv sync --frozen --no-dev`.
- **Runtime stage:** UBI9 Python 3.12, copy `.venv` and `src/` from build stage. Non-root user (UID 1001). Exposes port 8080.
- **Platform:** `ARG BUILD_PLATFORM=linux/amd64` passed to both `FROM` instructions for consistent cross-platform builds.
- **Entrypoint:** `CMD ["python", "-m", "rhoai_obs_mcp"]` which reads transport config from env vars.

## Server Entrypoint Changes

Add `src/rhoai_obs_mcp/__main__.py` that:

- Reads `MCP_TRANSPORT` env var (default `"sse"`)
- Reads `MCP_HOST` (default `"0.0.0.0"`) and `MCP_PORT` (default `"8080"`)
- Calls `create_server().run(transport=..., host=..., port=...)`

Remove the `if __name__ == "__main__"` block from `server.py` — it moves to `__main__.py`.

## OpenShift Manifests

All YAML in `deploy/`:

| File | Resource | Purpose |
|------|----------|---------|
| `serviceaccount.yaml` | ServiceAccount | `rhoai-obs-mcp` identity for the pod |
| `clusterrole.yaml` | ClusterRole | Read-only: pods, events, nodes, services, inferenceservices |
| `clusterrolebinding.yaml` | ClusterRoleBinding | Binds ClusterRole to ServiceAccount |
| `deployment.yaml` | Deployment | Single replica, port 8080, resource limits, env vars |
| `service.yaml` | Service | ClusterIP on port 8080 |
| `route.yaml` | Route | Edge-terminated TLS, exposes `/sse` externally |

### ClusterRole Permissions

```yaml
rules:
  - apiGroups: [""]
    resources: [pods, events, nodes, services]
    verbs: [get, list]
  - apiGroups: ["serving.kserve.io"]
    resources: [inferenceservices]
    verbs: [get, list]
```

### Deployment Details

- Resource requests: 128Mi memory, 100m CPU
- Resource limits: 256Mi memory, 500m CPU
- Liveness/readiness: TCP socket probe on port 8080
- SA token auto-mounted by Kubernetes
- Backend URLs configurable via env vars (same as local: `THANOS_URL`, `ALERTMANAGER_URL`, etc.)

## Build & Deploy Tooling

Makefile targets:

| Target | Command |
|--------|---------|
| `make build` | `$(CONTAINER_RUNTIME) build --platform=$(PLATFORM) -f Containerfile -t $(IMAGE) .` |
| `make push` | `$(CONTAINER_RUNTIME) push $(IMAGE)` |
| `make deploy` | `oc apply -f deploy/` |
| `make undeploy` | `oc delete -f deploy/` |

Variables: `IMAGE`, `CONTAINER_RUNTIME` (auto-detected, podman preferred), `PLATFORM` (default `linux/amd64`), `NAMESPACE`.

## Connection

MCP clients connect to `https://<route-hostname>/sse` after deployment.
