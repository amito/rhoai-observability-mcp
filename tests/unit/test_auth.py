from unittest.mock import patch

from rhoai_mcp.auth import AuthProvider
from rhoai_mcp.config import Settings


class TestAuthProvider:
    def test_explicit_token(self):
        """Should use explicitly provided token."""
        settings = Settings(_env_file=None, openshift_token="explicit-token-123")
        auth = AuthProvider(settings)
        assert auth.get_token() == "explicit-token-123"

    def test_auth_headers(self):
        """Should return proper bearer auth headers."""
        settings = Settings(_env_file=None, openshift_token="my-token")
        auth = AuthProvider(settings)
        headers = auth.get_headers()
        assert headers["Authorization"] == "Bearer my-token"

    @patch("rhoai_mcp.auth._read_sa_token")
    def test_in_cluster_token(self, mock_read):
        """Should read SA token when in-cluster and no explicit token."""
        mock_read.return_value = "sa-token-456"
        settings = Settings(_env_file=None)
        with patch.object(
            Settings, "is_in_cluster", new_callable=lambda: property(lambda self: True)
        ):
            auth = AuthProvider(settings)
            assert auth.get_token() == "sa-token-456"

    @patch("rhoai_mcp.auth._get_kubeconfig_token")
    def test_external_token(self, mock_kube):
        """Should use kubeconfig token when external and no explicit token."""
        mock_kube.return_value = "kube-token-789"
        settings = Settings(_env_file=None)
        auth = AuthProvider(settings)
        assert auth.get_token() == "kube-token-789"

    def test_no_token_available(self):
        """Should return None when no auth source is available."""
        settings = Settings(_env_file=None)
        with patch("rhoai_mcp.auth._get_kubeconfig_token", return_value=None):
            auth = AuthProvider(settings)
            assert auth.get_token() is None
