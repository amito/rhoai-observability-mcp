# GuideLLM + GPU Observability MCP Demo

Deploy vLLM on a GPU node, benchmark it with GuideLLM, then use the Observability MCP server to investigate GPU behavior via natural language.

The story: **Run load. Ask questions. Get answers with evidence.**

## Prerequisites

- OpenShift 4.16+ cluster with at least one GPU worker node
- NVIDIA GPU Operator and NFD Operator installed (DCGM exporter running)
- `oc` CLI authenticated with cluster-admin

No RHOAI, KServe, Service Mesh, or HuggingFace token required. The model (`Qwen/Qwen2.5-0.5B-Instruct`) is publicly available. Everything deploys as plain Kubernetes resources.

## Quick Start

```bash
./demos/guidellm-gpu-observability/deploy-e2e.sh
```

This will:
1. Verify a GPU node exists and DCGM exporter is running
2. Deploy vLLM (`Qwen/Qwen2.5-0.5B-Instruct`) in `vllm-demo` namespace
3. Validate model health and run a test inference
4. Deploy the Observability MCP server in `rhoai-obs-mcp` namespace
5. Grant monitoring RBAC for Thanos/Alertmanager API access
6. Validate MCP protocol (SSE handshake + tools/list + GPU metrics query)
7. Run GuideLLM benchmark (3 concurrency levels, ~6-8 min) and print results

## Step-by-Step Manual Deploy

### 1. Verify cluster and GPU

```bash
oc whoami
oc get nodes -l nvidia.com/gpu.count=1 \
  -o custom-columns='NAME:.metadata.name,GPU:.status.capacity.nvidia\.com/gpu,GPU_PRODUCT:.metadata.labels.nvidia\.com/gpu\.product'
oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter
```

### 2. Deploy vLLM

```bash
oc new-project vllm-demo
oc adm policy add-scc-to-user anyuid -z default -n vllm-demo
oc apply -f demos/guidellm-gpu-observability/vllm-deployment.yaml
oc rollout status deployment/vllm -n vllm-demo --timeout=600s
```

### 3. Validate vLLM

```bash
oc exec -n vllm-demo deploy/vllm -- curl -s http://localhost:8000/health
oc exec -n vllm-demo deploy/vllm -- curl -s http://localhost:8000/v1/models | python3 -m json.tool
oc exec -n vllm-demo deploy/vllm -- \
  curl -s http://localhost:8000/v1/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"Qwen/Qwen2.5-0.5B-Instruct","prompt":"What is Kubernetes?","max_tokens":64}' \
  | python3 -m json.tool
```

### 4. Deploy the Observability MCP server

```bash
oc new-project rhoai-obs-mcp
oc apply -f deploy/ -n rhoai-obs-mcp
oc adm policy add-cluster-role-to-user cluster-monitoring-view -z rhoai-obs-mcp -n rhoai-obs-mcp
oc apply -f demos/guidellm-gpu-observability/monitoring-rbac.yaml
oc adm policy add-cluster-role-to-user rhoai-obs-mcp-monitoring-api -z rhoai-obs-mcp -n rhoai-obs-mcp
oc rollout status deployment/rhoai-obs-mcp -n rhoai-obs-mcp --timeout=120s
echo "MCP endpoint:"
oc get route rhoai-obs-mcp -n rhoai-obs-mcp -o jsonpath='https://{.spec.host}/sse'
```

### 5. Run GuideLLM benchmark

```bash
oc apply -f demos/guidellm-gpu-observability/guidellm-job.yaml
oc logs -f job/guidellm-bench -n vllm-demo
```

### 6. Connect an MCP client

```bash
ROUTE_HOST=$(oc get route rhoai-obs-mcp -n rhoai-obs-mcp -o jsonpath='{.spec.host}')
claude mcp add rhoai-observability "https://${ROUTE_HOST}/sse"
```

Or for Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rhoai-observability": {
      "url": "https://<route-host>/sse"
    }
  }
}
```

## What to Ask the MCP

Once connected, try these prompts:

```
"Show me the GPU nodes and what's using them"
"What does GPU utilization look like across the cluster?"
"Investigate GPU behavior — compute utilization, VRAM, temperature, and power"
"Are there any active alerts? What's the overall cluster health?"
"Show me the pods and events in the vllm-demo namespace"
```

The MCP queries Thanos/Prometheus for DCGM GPU metrics, Alertmanager for alerts, and the OpenShift API for pod/node/event data — then explains the results in natural language with source attribution.

## Available GPU Metrics (DCGM)

The NVIDIA DCGM exporter provides these metrics through Thanos:

| Metric | What it tells you |
|--------|-------------------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU compute utilization (%) |
| `DCGM_FI_DEV_FB_USED` / `FB_FREE` | VRAM used/free (MiB) |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature (C) |
| `DCGM_FI_DEV_POWER_USAGE` | Power draw (W) |
| `DCGM_FI_DEV_SM_CLOCK` / `MEM_CLOCK` | SM/memory clock (MHz) |
| `DCGM_FI_PROF_GR_ENGINE_ACTIVE` | Graphics engine active ratio |
| `DCGM_FI_PROF_DRAM_ACTIVE` | Memory bandwidth utilization |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | Tensor core activity |
| `DCGM_FI_PROF_PCIE_TX_BYTES` / `RX_BYTES` | PCIe throughput |

## Known Gotchas

These were discovered during deployment and are already handled in the manifests:

1. **K8s Service naming conflict**: A Service named `vllm` causes Kubernetes to inject `VLLM_PORT` and `VLLM_SERVICE_HOST` env vars, which collide with vLLM's own `VLLM_PORT` variable (`ValueError: VLLM_PORT appears to be a URI`). The Service is named `vllm-server` to avoid this.

2. **OpenShift SCC**: The upstream `vllm/vllm-openai` image runs as root. The deploy script grants `anyuid` SCC to the default ServiceAccount in the `vllm-demo` namespace.

3. **Cache directory permissions**: The upstream image needs writable cache dirs. The manifest sets `HF_HOME`, `TRANSFORMERS_CACHE`, and `XDG_CACHE_HOME` to `/tmp/hf-cache` backed by an emptyDir volume.

4. **GuideLLM CLI syntax**: Recent versions of GuideLLM use `guidellm benchmark run --target ...` (not the older `guidellm --target ...`). The job manifest has the correct syntax.

## Files

| File | Purpose |
|------|---------|
| `deploy-e2e.sh` | Full deployment, validation, and benchmark script |
| `teardown.sh` | Clean removal of all resources |
| `vllm-deployment.yaml` | vLLM Deployment + Service (with gotcha fixes) |
| `guidellm-job.yaml` | GuideLLM benchmark Job (concurrent profile, 3 rates) |
| `monitoring-rbac.yaml` | ClusterRole for Prometheus/Alertmanager API access |

## Teardown

```bash
./demos/guidellm-gpu-observability/teardown.sh
```

Or manually:

```bash
oc delete job/guidellm-bench -n vllm-demo
oc delete deployment/vllm service/vllm-server -n vllm-demo
oc delete project vllm-demo
oc delete -f deploy/ -n rhoai-obs-mcp
oc delete clusterrole rhoai-obs-mcp-monitoring-api
oc delete project rhoai-obs-mcp
```

## Architecture

```
+------------------+     natural language      +-------------------+
|  Claude Desktop  | -----------------------> |  Observability    |
|  or Claude Code  | <----------------------- |  MCP Server       |
+------------------+   structured evidence     | (rhoai-obs-mcp)   |
                                               +--------+----------+
                                                        |
                                    +-------------------+-------------------+
                                    |                   |                   |
                              +-----v-----+      +-----v------+     +-----v------+
                              |  Thanos   |      | Alertmanager|     | OpenShift  |
                              |  Querier  |      |             |     | API        |
                              +-----+-----+      +------------+     +-----+------+
                                    |                                      |
                          +---------+---------+                     +------+------+
                          |                   |                     |             |
                    +-----v-----+       +-----v-----+        +-----v---+   +-----v----+
                    |  DCGM     |       | Prometheus |       | Pods    |   | Events   |
                    |  Exporter |       | (cluster)  |       | Nodes   |   |          |
                    +-----+-----+       +-----------+        +---------+   +----------+
                          |
                    +-----v-----+
                    | GPU       |  <--- vLLM (Qwen2.5-0.5B-Instruct)
                    |           |  <--- GuideLLM benchmark
                    +-----------+
```
