from __future__ import annotations

import asyncio
import json
from aiohttp import web

from .config import AppConfig
from .executor import TaskExecutor
from .models import TaskRecord, TaskRequest, new_task_id
from .sanitizer import sanitize_text
from .store import InMemoryStore


class BridgeServer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = InMemoryStore(config.lane_profiles)
        self.executor = TaskExecutor(self.store, config)

    @web.middleware
    async def auth_middleware(self, request: web.Request, handler):
        if request.path == "/health":
            return await handler(request)
        expected = f"Bearer {self.config.bearer_token}"
        provided = request.headers.get("Authorization", "")
        if provided != expected:
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        return await handler(request)

    @web.middleware
    async def json_error_middleware(self, request: web.Request, handler):
        try:
            return await handler(request)
        except json.JSONDecodeError:
            return web.json_response({"ok": False, "error": "invalid json body"}, status=400)
        except web.HTTPException:
            raise
        except Exception as exc:  # pragma: no cover
            return web.json_response({"ok": False, "error": sanitize_text(str(exc))}, status=500)

    def app(self) -> web.Application:
        app = web.Application(middlewares=[self.json_error_middleware, self.auth_middleware])
        app.add_routes([
            web.get("/health", self.health),
            web.get("/lanes", self.list_lanes),
            web.get(r"/lanes/{lane_id}", self.get_lane),
            web.post("/tasks", self.create_task),
            web.get(r"/tasks/{task_id}", self.get_task),
            web.post(r"/tasks/{task_id}/cancel", self.cancel_task),
            web.get(r"/tasks/{task_id}/artifacts", self.get_artifacts),
        ])
        return app

    async def health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "service": "hermes-opencode-bridge", "executor_mode": self.config.executor_mode})

    async def list_lanes(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "lanes": [lane.to_dict() for lane in self.store.lanes()]})

    async def get_lane(self, request: web.Request) -> web.Response:
        lane = self.store.get_lane(request.match_info["lane_id"])
        if lane is None:
            return web.json_response({"ok": False, "error": "lane not found"}, status=404)
        return web.json_response({"ok": True, "lane": lane.to_dict()})

    async def create_task(self, request: web.Request) -> web.Response:
        payload = await request.json()
        if not isinstance(payload, dict):
            return web.json_response({"ok": False, "error": "json body must be an object"}, status=400)
        task_request = TaskRequest.from_payload(payload)
        errors = task_request.validate()
        if errors:
            return web.json_response({"ok": False, "errors": errors}, status=400)
        lane = self.store.get_lane(task_request.lane_id)
        if lane is None:
            return web.json_response({"ok": False, "error": "lane not found"}, status=404)
        if not lane.opencode_ready:
            return web.json_response({"ok": False, "error": f"lane {lane.lane_id} is not OpenCode-ready; dedicated lanes must execute through their OpenCode worker only"}, status=409)
        task = TaskRecord(
            task_id=new_task_id(),
            lane_id=task_request.lane_id,
            text=sanitize_text(task_request.text),
            directory=task_request.directory,
            metadata={"session_id": task_request.session_id, "agent": task_request.agent, "timeout_ms": task_request.timeout_ms},
        )
        self.store.add_task(task)
        asyncio.create_task(self.executor.execute(task))
        return web.json_response({"ok": True, "task": task.to_dict()}, status=202)

    async def get_task(self, request: web.Request) -> web.Response:
        task = self.store.get_task(request.match_info["task_id"])
        if task is None:
            return web.json_response({"ok": False, "error": "task not found"}, status=404)
        return web.json_response({"ok": True, "task": task.to_dict()})

    async def cancel_task(self, request: web.Request) -> web.Response:
        task = self.store.request_cancel(request.match_info["task_id"])
        if task is None:
            return web.json_response({"ok": False, "error": "task not found"}, status=404)
        return web.json_response({"ok": True, "task": task.to_dict()})

    async def get_artifacts(self, request: web.Request) -> web.Response:
        task = self.store.get_task(request.match_info["task_id"])
        if task is None:
            return web.json_response({"ok": False, "error": "task not found"}, status=404)
        return web.json_response({"ok": True, "artifacts": [artifact.to_dict() for artifact in task.artifacts]})
