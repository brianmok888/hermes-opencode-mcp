from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any

from .config import AppConfig
from .service import LaneService, ServiceError


class MCPServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.service = LaneService(config)

    async def run(self) -> int:
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                return 0
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                await self._send({"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}, "id": None})
                continue
            response = await self._handle_request(request)
            if response is not None:
                await self._send(response)

    async def _handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if not method:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "invalid request"}}
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.config.server_name, "version": self.config.server_version},
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                }
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                result = {"tools": self.service.tools_schema()}
            elif method == "tools/call":
                result = await self.service.call_tool(str(params.get("name", "")), params.get("arguments") or {})
            elif method == "resources/list":
                result = {"resources": self.service.list_resources()}
            elif method == "resources/read":
                result = {"contents": [self.service.read_resource(str(params.get("uri", "")))]}
            elif method == "prompts/list":
                result = {"prompts": self.service.list_prompts()}
            elif method == "prompts/get":
                result = self.service.get_prompt(str(params.get("name", "")), params.get("arguments") or {})
            elif method == "ping":
                result = {"ok": True}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"method not found: {method}"},
                }
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except ServiceError as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32001, "message": str(exc), "data": traceback.format_exc(limit=5)},
            }

    async def _send(self, payload: dict[str, Any]) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        await asyncio.to_thread(sys.stdout.write, text + "\n")
        await asyncio.to_thread(sys.stdout.flush)
