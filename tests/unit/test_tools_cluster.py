# tests/unit/test_tools_cluster.py
import pytest
from unittest.mock import MagicMock
from rhoai_obs_mcp.tools.cluster import register_cluster_tools


class TestClusterTools:
    def setup_method(self):
        self.openshift = MagicMock()
        self.tools = register_cluster_tools(self.openshift)

    @pytest.mark.asyncio
    async def test_get_pods(self):
        """Should return formatted pod list."""
        self.openshift.get_pods.return_value = [
            {
                "name": "vllm-0",
                "namespace": "vllm",
                "status": "Running",
                "restarts": 0,
                "created": "2024-01-01",
            },
        ]

        result = await self.tools["get_pods"](namespace="vllm")
        assert "vllm-0" in result
        assert "Running" in result

    @pytest.mark.asyncio
    async def test_get_events(self):
        """Should return formatted events."""
        self.openshift.get_events.return_value = [
            {
                "reason": "Pulled",
                "message": "Container image pulled",
                "type": "Normal",
                "count": 1,
                "object": "Pod/vllm-0",
                "timestamp": "2024-01-01",
            },
        ]

        result = await self.tools["get_events"](namespace="vllm")
        assert "Pulled" in result

    @pytest.mark.asyncio
    async def test_get_node_status(self):
        """Should return formatted node info."""
        self.openshift.get_nodes.return_value = [
            {
                "name": "gpu-node-1",
                "conditions": {"Ready": "True"},
                "capacity": {"nvidia.com/gpu": "4"},
                "allocatable": {"nvidia.com/gpu": "2"},
            },
        ]

        result = await self.tools["get_node_status"]()
        assert "gpu-node-1" in result
        assert "nvidia.com/gpu" in result

    @pytest.mark.asyncio
    async def test_get_inference_services(self):
        """Should return formatted InferenceService list."""
        self.openshift.get_inference_services.return_value = [
            {
                "metadata": {"name": "llama-service", "namespace": "vllm"},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            },
        ]

        result = await self.tools["get_inference_services"](namespace="vllm")
        assert "llama-service" in result
