# src/rhoai_mcp/backends/openshift.py
import logging

from kubernetes import client, config as k8s_config

from rhoai_mcp.auth import AuthProvider
from rhoai_mcp.config import Settings

# Re-export for easy patching in tests
config = k8s_config

logger = logging.getLogger(__name__)


class OpenShiftBackend:
    """Kubernetes/OpenShift API client."""

    def __init__(self, settings: Settings, auth: AuthProvider) -> None:
        self._settings = settings
        self._auth = auth
        self._configure_client()

    def _configure_client(self) -> None:
        """Configure the Kubernetes client based on environment."""
        try:
            if self._settings.is_in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
        except Exception:
            logger.warning("Could not auto-configure Kubernetes client")

        # If an explicit token is provided, configure it
        token = self._auth.get_token()
        if token:
            configuration = client.Configuration.get_default_copy()
            configuration.api_key = {"authorization": f"Bearer {token}"}
            client.Configuration.set_default(configuration)

    def _core_v1(self) -> client.CoreV1Api:
        return client.CoreV1Api()

    def _custom_objects(self) -> client.CustomObjectsApi:
        return client.CustomObjectsApi()

    def get_pods(
        self,
        namespace: str,
        label_selector: str | None = None,
        field_selector: str | None = None,
    ) -> list[dict]:
        """List pods in a namespace."""
        try:
            kwargs: dict = {"namespace": namespace}
            if label_selector:
                kwargs["label_selector"] = label_selector
            if field_selector:
                kwargs["field_selector"] = field_selector

            pods = self._core_v1().list_namespaced_pod(**kwargs)
            return [
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "restarts": sum(
                        cs.restart_count for cs in (pod.status.container_statuses or [])
                    ),
                    "created": str(pod.metadata.creation_timestamp),
                }
                for pod in pods.items
            ]
        except Exception as exc:
            logger.error("Failed to list pods: %s", exc)
            return []

    def get_events(
        self,
        namespace: str,
        resource_name: str | None = None,
        reason: str | None = None,
    ) -> list[dict]:
        """List events in a namespace."""
        try:
            kwargs: dict = {"namespace": namespace}
            if resource_name:
                kwargs["field_selector"] = f"involvedObject.name={resource_name}"

            events = self._core_v1().list_namespaced_event(**kwargs)
            result = []
            for event in events.items:
                if reason and event.reason != reason:
                    continue
                result.append(
                    {
                        "reason": event.reason,
                        "message": event.message,
                        "type": event.type,
                        "count": event.count,
                        "object": f"{event.involved_object.kind}/{event.involved_object.name}",
                        "timestamp": str(event.metadata.creation_timestamp),
                    }
                )
            return result
        except Exception as exc:
            logger.error("Failed to list events: %s", exc)
            return []

    def get_nodes(self, node_name: str | None = None) -> list[dict]:
        """Get node status information."""
        try:
            if node_name:
                node = self._core_v1().read_node(node_name)
                nodes = [node]
            else:
                node_list = self._core_v1().list_node()
                nodes = node_list.items

            return [
                {
                    "name": node.metadata.name,
                    "conditions": {c.type: c.status for c in (node.status.conditions or [])},
                    "capacity": dict(node.status.capacity or {}),
                    "allocatable": dict(node.status.allocatable or {}),
                }
                for node in nodes
            ]
        except Exception as exc:
            logger.error("Failed to get node status: %s", exc)
            return []

    def get_inference_services(self, namespace: str | None = None) -> list[dict]:
        """List KServe InferenceService resources."""
        try:
            api = self._custom_objects()
            if namespace:
                result = api.list_namespaced_custom_object(
                    group="serving.kserve.io",
                    version="v1beta1",
                    namespace=namespace,
                    plural="inferenceservices",
                )
            else:
                result = api.list_cluster_custom_object(
                    group="serving.kserve.io",
                    version="v1beta1",
                    plural="inferenceservices",
                )
            return result.get("items", [])
        except Exception as exc:
            logger.error("Failed to list InferenceServices: %s", exc)
            return []

    def describe_resource(self, resource_type: str, name: str, namespace: str) -> dict:
        """Get detailed info about a specific resource."""
        try:
            v1 = self._core_v1()
            if resource_type == "pod":
                obj = v1.read_namespaced_pod(name, namespace)
            elif resource_type == "service":
                obj = v1.read_namespaced_service(name, namespace)
            elif resource_type == "node":
                obj = v1.read_node(name)
            else:
                return {"error": f"Unsupported resource type: {resource_type}"}
            return obj.to_dict()
        except Exception as exc:
            logger.error("Failed to describe %s/%s: %s", resource_type, name, exc)
            return {"error": str(exc)}
