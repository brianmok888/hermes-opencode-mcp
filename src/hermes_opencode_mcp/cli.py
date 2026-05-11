from __future__ import annotations

import asyncio
import sys

from .config import ConfigError, load_config
from .mcp_server import MCPServer


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f'CONFIG ERROR: {exc}', file=sys.stderr)
        return 2
    server = MCPServer(config)
    return asyncio.run(server.run())


if __name__ == '__main__':
    raise SystemExit(main())
