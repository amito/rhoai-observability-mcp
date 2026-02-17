import json

from rhoai_mcp.backends.openshift import OpenShiftBackend


def register_cluster_tools(openshift: OpenShiftBackend) -> dict:
    """Create cluster tool functions bound to the given backend."""

    async def get_pods(
        namespace: str,
        label_selector: str | None = None,
        field_selector: str | None = None,
    ) -> str:
        """List pods in a namespace with their status.

        Args:
            namespace: Kubernetes namespace to list pods from
            label_selector: Filter by labels (e.g., 'app=vllm')
            field_selector: Filter by fields (e.g., 'status.phase=Running')
        """
        pods = openshift.get_pods(namespace, label_selector, field_selector)

        if not pods:
            return f"No pods found in namespace '{namespace}'."

        lines = [f"## Pods in namespace: {namespace} ({len(pods)} total)\n"]
        for pod in pods:
            lines.append(
                f"- **{pod['name']}**: {pod['status']} "
                f"(restarts: {pod['restarts']}, created: {pod['created']})"
            )

        return "\n".join(lines)

    async def get_events(
        namespace: str,
        resource_name: str | None = None,
        reason: str | None = None,
    ) -> str:
        """List Kubernetes events in a namespace.

        Args:
            namespace: Kubernetes namespace
            resource_name: Filter events for a specific resource
            reason: Filter by event reason (e.g., 'BackOff', 'Pulled', 'Failed')
        """
        events = openshift.get_events(namespace, resource_name, reason)

        if not events:
            return f"No events found in namespace '{namespace}'."

        lines = [f"## Events in namespace: {namespace} ({len(events)} total)\n"]
        for event in events:
            lines.append(
                f"- [{event['type']}] **{event['reason']}**: "
                f"{event['message']} ({event['object']}, x{event['count']})"
            )

        return "\n".join(lines)

    async def get_node_status(node_name: str | None = None) -> str:
        """Get node status, capacity, and GPU allocation info.

        Args:
            node_name: Specific node name, or omit for all nodes
        """
        nodes = openshift.get_nodes(node_name)

        if not nodes:
            return "No nodes found."

        lines = ["## Node Status\n"]
        for node in nodes:
            conditions = node.get("conditions", {})
            ready = conditions.get("Ready", "Unknown")
            lines.append(f"### {node['name']} (Ready: {ready})")

            capacity = node.get("capacity", {})
            allocatable = node.get("allocatable", {})

            gpu_cap = capacity.get("nvidia.com/gpu", "0")
            gpu_alloc = allocatable.get("nvidia.com/gpu", "0")
            if gpu_cap != "0":
                lines.append(
                    f"- **GPU:** {gpu_alloc} available / {gpu_cap} total (nvidia.com/gpu)"
                )

            lines.append(
                f"- **CPU:** {allocatable.get('cpu', 'N/A')} available "
                f"/ {capacity.get('cpu', 'N/A')} total"
            )
            lines.append(
                f"- **Memory:** {allocatable.get('memory', 'N/A')} available "
                f"/ {capacity.get('memory', 'N/A')} total"
            )
            lines.append("")

        return "\n".join(lines)

    async def describe_resource(
        resource_type: str, name: str, namespace: str
    ) -> str:
        """Get detailed description of a Kubernetes resource.

        Args:
            resource_type: Resource type ('pod', 'service', 'node')
            name: Resource name
            namespace: Kubernetes namespace
        """
        result = openshift.describe_resource(resource_type, name, namespace)
        if "error" in result:
            return f"Error describing {resource_type}/{name}: {result['error']}"
        return json.dumps(result, indent=2, default=str)

    async def get_inference_services(namespace: str | None = None) -> str:
        """List KServe InferenceService resources.

        Args:
            namespace: Namespace to search, or omit for all namespaces
        """
        services = openshift.get_inference_services(namespace)

        if not services:
            scope = f"namespace '{namespace}'" if namespace else "the cluster"
            return f"No InferenceServices found in {scope}."

        lines = [f"## InferenceServices ({len(services)} total)\n"]
        for svc in services:
            meta = svc.get("metadata", {})
            status = svc.get("status", {})
            conditions = status.get("conditions", [])
            ready = next((c for c in conditions if c.get("type") == "Ready"), {})
            ready_status = ready.get("status", "Unknown")
            lines.append(
                f"- **{meta.get('name', 'unknown')}** "
                f"({meta.get('namespace', '')}): Ready={ready_status}"
            )

        return "\n".join(lines)

    return {
        "get_pods": get_pods,
        "get_events": get_events,
        "get_node_status": get_node_status,
        "describe_resource": describe_resource,
        "get_inference_services": get_inference_services,
    }
