# tests/unit/test_backends_openshift.py
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from rhoai_obs_mcp.backends.openshift import OpenShiftBackend


def _make_pod(name, namespace, phase="Running", restarts=0):
    """Helper to create a mock V1Pod."""
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.metadata.creation_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    pod.status.phase = phase
    container_status = MagicMock()
    container_status.restart_count = restarts
    container_status.name = "main"
    container_status.ready = True
    pod.status.container_statuses = [container_status]
    return pod


def _make_event(reason, message, namespace="vllm"):
    event = MagicMock()
    event.reason = reason
    event.message = message
    event.metadata.namespace = namespace
    event.metadata.creation_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    event.involved_object.kind = "Pod"
    event.involved_object.name = "vllm-0"
    event.type = "Warning"
    event.count = 1
    return event


class TestOpenShiftBackend:
    @patch("rhoai_obs_mcp.backends.openshift.config")
    @patch("rhoai_obs_mcp.backends.openshift.client")
    def test_get_pods(self, mock_client, mock_config, settings, auth):
        """Should list pods in a namespace."""
        mock_v1 = MagicMock()
        mock_client.CoreV1Api.return_value = mock_v1

        pod_list = MagicMock()
        pod_list.items = [_make_pod("vllm-0", "vllm"), _make_pod("vllm-1", "vllm")]
        mock_v1.list_namespaced_pod.return_value = pod_list

        backend = OpenShiftBackend(settings, auth)
        result = backend.get_pods("vllm")
        assert len(result) == 2
        assert result[0]["name"] == "vllm-0"
        assert result[0]["status"] == "Running"

    @patch("rhoai_obs_mcp.backends.openshift.config")
    @patch("rhoai_obs_mcp.backends.openshift.client")
    def test_get_events(self, mock_client, mock_config, settings, auth):
        """Should list events in a namespace."""
        mock_v1 = MagicMock()
        mock_client.CoreV1Api.return_value = mock_v1

        event_list = MagicMock()
        event_list.items = [_make_event("BackOff", "Back-off restarting failed container")]
        mock_v1.list_namespaced_event.return_value = event_list

        backend = OpenShiftBackend(settings, auth)
        result = backend.get_events("vllm")
        assert len(result) == 1
        assert result[0]["reason"] == "BackOff"

    @patch("rhoai_obs_mcp.backends.openshift.config")
    @patch("rhoai_obs_mcp.backends.openshift.client")
    def test_get_nodes(self, mock_client, mock_config, settings, auth):
        """Should list node status."""
        mock_v1 = MagicMock()
        mock_client.CoreV1Api.return_value = mock_v1

        node = MagicMock()
        node.metadata.name = "gpu-node-1"
        condition = MagicMock()
        condition.type = "Ready"
        condition.status = "True"
        node.status.conditions = [condition]
        node.status.capacity = {"nvidia.com/gpu": "4", "cpu": "32", "memory": "128Gi"}
        node.status.allocatable = {"nvidia.com/gpu": "2", "cpu": "30", "memory": "120Gi"}

        node_list = MagicMock()
        node_list.items = [node]
        mock_v1.list_node.return_value = node_list

        backend = OpenShiftBackend(settings, auth)
        result = backend.get_nodes()
        assert len(result) == 1
        assert result[0]["name"] == "gpu-node-1"
        assert result[0]["capacity"]["nvidia.com/gpu"] == "4"
