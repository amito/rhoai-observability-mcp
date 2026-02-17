from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

_SA_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")


class Settings(BaseSettings):
    """Configuration for the RHOAI Observability MCP server."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Backend URLs (auto-detected if not set)
    thanos_url: str | None = Field(default=None, description="ThanosQuerier URL")
    alertmanager_url: str | None = Field(default=None, description="Alertmanager URL")
    loki_url: str | None = Field(default=None, description="LokiStack gateway URL")
    grafana_url: str | None = Field(default=None, description="Grafana URL")

    # Auth
    openshift_token: str | None = Field(default=None, description="Bearer token override")

    # Behavior
    default_time_range: str = Field(default="5m", description="Default PromQL/LogQL time range")
    log_level: str = Field(default="INFO", description="Logging level")
    request_timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")

    @property
    def is_in_cluster(self) -> bool:
        """Detect if running inside an OpenShift/Kubernetes cluster."""
        return _SA_TOKEN_PATH.exists()
