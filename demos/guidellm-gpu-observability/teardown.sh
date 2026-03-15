#!/usr/bin/env bash
# Teardown: remove all demo resources
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[INFO] Removing GuideLLM job"
oc delete job/guidellm-bench -n vllm-demo 2>/dev/null || true

echo "[INFO] Removing vLLM"
oc delete deployment/vllm service/vllm-server -n vllm-demo 2>/dev/null || true
oc delete project vllm-demo 2>/dev/null || true

echo "[INFO] Removing MCP server"
oc delete -f "${REPO_ROOT}/deploy/" -n rhoai-obs-mcp 2>/dev/null || true
oc delete clusterrole rhoai-obs-mcp-monitoring-api 2>/dev/null || true
oc delete project rhoai-obs-mcp 2>/dev/null || true

echo "[INFO] Teardown complete"
