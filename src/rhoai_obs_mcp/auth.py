import logging
import subprocess
from pathlib import Path

from rhoai_obs_mcp.config import Settings

logger = logging.getLogger(__name__)

_SA_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")


def _read_sa_token() -> str | None:
    """Read the ServiceAccount token from the mounted secret."""
    try:
        return _SA_TOKEN_PATH.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None


def _get_kubeconfig_token() -> str | None:
    """Extract token from current kubeconfig context via oc/kubectl."""
    for cmd in ["oc", "kubectl"]:
        try:
            result = subprocess.run(
                [cmd, "whoami", "--token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


class AuthProvider:
    """Manages authentication tokens for backend access."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cached_token: str | None = None

    def get_token(self) -> str | None:
        """Get the current auth token, using the best available source."""
        if self._settings.openshift_token:
            return self._settings.openshift_token

        if self._cached_token:
            return self._cached_token

        if self._settings.is_in_cluster:
            self._cached_token = _read_sa_token()
        else:
            self._cached_token = _get_kubeconfig_token()

        return self._cached_token

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers with authorization."""
        token = self.get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def clear_cache(self) -> None:
        """Clear the cached token, forcing re-detection on next call."""
        self._cached_token = None
