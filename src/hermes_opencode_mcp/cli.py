from __future__ import annotations

import asyncio
import sys

from .config import ConfigError, load_config
from .logging_utils import configure_logging, get_logger
from .mcp_server import MCPServer


logger = get_logger(__name__)


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f'CONFIG ERROR: {exc}', file=sys.stderr)
        return 2
    configure_logging(level=config.log_level, json_logs=config.log_json)
    server = MCPServer(config)
    try:
        return asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("server_shutdown_requested", extra={"event_data": {"reason": "keyboard_interrupt"}})
        return 130
    except Exception:
        logger.exception("server_crashed")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
