import os
from unittest.mock import patch

from rhoai_obs_mcp.__main__ import main


class TestMain:
    @patch("rhoai_obs_mcp.__main__.create_server")
    def test_main_defaults_to_sse(self, mock_create_server):
        """Default transport should be SSE for container deployment."""
        mock_server = mock_create_server.return_value
        main()
        mock_create_server.assert_called_once_with(host="0.0.0.0", port=8080)
        mock_server.run.assert_called_once_with(transport="sse")

    @patch("rhoai_obs_mcp.__main__.create_server")
    def test_main_reads_transport_env(self, mock_create_server):
        """MCP_TRANSPORT env var should override default."""
        mock_server = mock_create_server.return_value
        with patch.dict(os.environ, {"MCP_TRANSPORT": "stdio"}):
            main()
        mock_server.run.assert_called_once_with(transport="stdio")

    @patch("rhoai_obs_mcp.__main__.create_server")
    def test_main_reads_host_port_env(self, mock_create_server):
        """MCP_HOST and MCP_PORT env vars should configure the server."""
        mock_server = mock_create_server.return_value
        with patch.dict(os.environ, {"MCP_HOST": "127.0.0.1", "MCP_PORT": "9090"}):
            main()
        mock_create_server.assert_called_once_with(host="127.0.0.1", port=9090)
