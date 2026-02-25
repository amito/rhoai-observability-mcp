import os
from typing import Literal, cast

from rhoai_obs_mcp.server import create_server

Transport = Literal["stdio", "sse", "streamable-http"]


def main() -> None:
    """Entrypoint for `python -m rhoai_obs_mcp`."""
    transport = cast(Transport, os.environ.get("MCP_TRANSPORT", "sse"))
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))

    server = create_server(host=host, port=port)
    server.run(transport=transport)


if __name__ == "__main__":
    main()
