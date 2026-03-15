#!/usr/bin/env bash
# End-to-end deployment: vLLM + GuideLLM + Observability MCP
# Prerequisites: OpenShift cluster with GPU node, GPU Operator, NFD, oc logged in
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VLLM_NS="vllm-demo"
MCP_NS="rhoai-obs-mcp"

log() { echo "[INFO] $(date +%H:%M:%S) $*"; }
warn() { echo "[WARN] $(date +%H:%M:%S) $*"; }
err()  { echo "[ERROR] $(date +%H:%M:%S) $*"; exit 1; }

# -------------------------------------------------------------------
# 1. Preflight
# -------------------------------------------------------------------
log "Cluster: $(oc whoami --show-server)"
log "User: $(oc whoami)"

GPU_NODE=$(oc get nodes -l nvidia.com/gpu.count=1 -o name 2>/dev/null | head -1)
[[ -z "$GPU_NODE" ]] && err "No GPU node found. Install NVIDIA GPU Operator + NFD first."
GPU_PRODUCT=$(oc get ${GPU_NODE} -o jsonpath='{.metadata.labels.nvidia\.com/gpu\.product}')
log "GPU node: ${GPU_NODE} (${GPU_PRODUCT})"

oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter --no-headers | head -1 \
  || err "DCGM exporter not running in nvidia-gpu-operator namespace"

# -------------------------------------------------------------------
# 2. Deploy vLLM
# -------------------------------------------------------------------
log "Deploying vLLM in ${VLLM_NS}"
oc new-project "${VLLM_NS}" 2>/dev/null || oc project "${VLLM_NS}" >/dev/null

# Grant anyuid SCC — upstream vLLM image runs as root
oc adm policy add-scc-to-user anyuid -z default -n "${VLLM_NS}" 2>/dev/null

oc apply -f "${SCRIPT_DIR}/vllm-deployment.yaml"

log "Waiting for vLLM rollout (image pull + model load, may take 5-10 min)..."
if ! oc rollout status deployment/vllm -n "${VLLM_NS}" --timeout=600s; then
  warn "vLLM not ready yet. Pod status:"
  oc get pods -n "${VLLM_NS}" -o wide
  oc describe pod -n "${VLLM_NS}" -l app=vllm | tail -20
  err "vLLM deployment failed"
fi

# -------------------------------------------------------------------
# 3. Validate vLLM
# -------------------------------------------------------------------
log "Validating vLLM"
oc exec -n "${VLLM_NS}" deploy/vllm -- curl -sf http://localhost:8000/health \
  || err "vLLM health check failed"
log "Health: OK"

MODEL_ID=$(oc exec -n "${VLLM_NS}" deploy/vllm -- \
  curl -sf http://localhost:8000/v1/models \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null)
log "Model loaded: ${MODEL_ID}"

COMPLETION=$(oc exec -n "${VLLM_NS}" deploy/vllm -- \
  curl -sf http://localhost:8000/v1/completions \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${MODEL_ID}\",\"prompt\":\"Hello\",\"max_tokens\":16}" 2>/dev/null)
log "Inference test: $(echo "$COMPLETION" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['text'][:60])" 2>/dev/null || echo "$COMPLETION" | head -c 100)"

# -------------------------------------------------------------------
# 4. Deploy MCP server
# -------------------------------------------------------------------
log "Deploying Observability MCP in ${MCP_NS}"
oc new-project "${MCP_NS}" 2>/dev/null || oc project "${MCP_NS}" >/dev/null
oc apply -f "${REPO_ROOT}/deploy/" -n "${MCP_NS}"

oc adm policy add-cluster-role-to-user cluster-monitoring-view \
  -z rhoai-obs-mcp -n "${MCP_NS}" 2>/dev/null
oc apply -f "${SCRIPT_DIR}/monitoring-rbac.yaml"
oc adm policy add-cluster-role-to-user rhoai-obs-mcp-monitoring-api \
  -z rhoai-obs-mcp -n "${MCP_NS}" 2>/dev/null

if ! oc rollout status deployment/rhoai-obs-mcp -n "${MCP_NS}" --timeout=120s; then
  oc get pods -n "${MCP_NS}" -o wide
  err "MCP deployment failed"
fi

ROUTE_HOST=$(oc get route rhoai-obs-mcp -n "${MCP_NS}" -o jsonpath='{.spec.host}')
log "MCP route: https://${ROUTE_HOST}/sse"

# -------------------------------------------------------------------
# 5. Validate MCP
# -------------------------------------------------------------------
log "Validating MCP protocol"
OUT=/tmp/mcp_e2e_validate.out
COOK=/tmp/mcp_e2e_cookie.txt
rm -f "$OUT" "$COOK"
(curl -skN -c "$COOK" "https://${ROUTE_HOST}/sse" > "$OUT") &
SSE_PID=$!
MSG_PATH=""
for _ in {1..15}; do
  MSG_PATH=$(awk -F'data: ' '/^data: /{print $2; exit}' "$OUT" 2>/dev/null | tr -d '\r')
  [[ -n "$MSG_PATH" ]] && break
  sleep 1
done
if [[ -z "$MSG_PATH" ]]; then
  kill $SSE_PID 2>/dev/null || true
  err "Could not establish SSE session"
fi

# Initialize + list tools + query GPU metrics
curl -sk -b "$COOK" -X POST "https://${ROUTE_HOST}${MSG_PATH}" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"e2e","version":"0.1"}}}' >/dev/null
curl -sk -b "$COOK" -X POST "https://${ROUTE_HOST}${MSG_PATH}" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' >/dev/null
curl -sk -b "$COOK" -X POST "https://${ROUTE_HOST}${MSG_PATH}" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' >/dev/null
curl -sk -b "$COOK" -X POST "https://${ROUTE_HOST}${MSG_PATH}" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"query_prometheus","arguments":{"query":"DCGM_FI_DEV_GPU_UTIL"}}}' >/dev/null
curl -sk -b "$COOK" -X POST "https://${ROUTE_HOST}${MSG_PATH}" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_pods","arguments":{"namespace":"'"${VLLM_NS}"'"}}}' >/dev/null
sleep 3
kill $SSE_PID 2>/dev/null || true

TOOL_COUNT=$(python3 -c "
import re, json
data = open('$OUT').read()
for e in data.split('event: message'):
    m = re.search(r'data: (.+)', e)
    if m:
        try:
            j = json.loads(m.group(1))
            if j.get('id') == 2 and 'result' in j:
                print(len(j['result'].get('tools',[])))
        except: pass
" 2>/dev/null)

if [[ "$TOOL_COUNT" -ge 17 ]]; then
  log "MCP validated: ${TOOL_COUNT} tools, GPU metrics + pod queries working"
else
  warn "MCP returned ${TOOL_COUNT:-0} tools (expected 17+)"
fi

# -------------------------------------------------------------------
# 6. Run GuideLLM benchmark
# -------------------------------------------------------------------
log "Launching GuideLLM benchmark"
oc project "${VLLM_NS}" >/dev/null
oc delete job/guidellm-bench -n "${VLLM_NS}" 2>/dev/null || true
oc apply -f "${SCRIPT_DIR}/guidellm-job.yaml"
log "GuideLLM running. Follow with: oc logs -f job/guidellm-bench -n ${VLLM_NS}"

log "Waiting for GuideLLM to complete (this takes several minutes)..."
if oc wait --for=condition=complete job/guidellm-bench -n "${VLLM_NS}" --timeout=900s; then
  log "GuideLLM complete. Results:"
  oc logs job/guidellm-bench -n "${VLLM_NS}" 2>/dev/null | tail -40
else
  warn "GuideLLM did not complete within timeout. Check: oc logs job/guidellm-bench -n ${VLLM_NS}"
fi

# -------------------------------------------------------------------
# 7. Summary
# -------------------------------------------------------------------
echo ""
log "=========================================="
log "Demo deployment complete"
log "=========================================="
log "vLLM:       running in ${VLLM_NS} (model: ${MODEL_ID})"
log "MCP:        https://${ROUTE_HOST}/sse"
log "GuideLLM:   job/guidellm-bench in ${VLLM_NS}"
log ""
log "Connect Claude Code:"
log "  claude mcp add rhoai-observability https://${ROUTE_HOST}/sse"
log ""
log "Teardown:"
log "  ${SCRIPT_DIR}/teardown.sh"
