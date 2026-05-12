from __future__ import annotations

import sys
from aiohttp import web

from .config import ConfigError, load_config
from .server import BridgeServer


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    server = BridgeServer(config)
    web.run_app(server.app(), host=config.host, port=config.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
