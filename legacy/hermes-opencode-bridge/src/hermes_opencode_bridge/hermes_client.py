from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .sanitizer import sanitize_text


class BridgeClientError(RuntimeError):
    pass


@dataclass(slots=True)
class BridgeClientConfig:
    base_url: str
    bearer_token: str
    timeout_seconds: int = 20
    poll_interval_seconds: float = 1.0


class BridgeClient:
    def __init__(self, config: BridgeClientConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip('/')

    def _request(self, path: str, *, method: str = 'GET', payload: dict[str, Any] | None = None, auth: bool = True) -> dict[str, Any]:
        headers: dict[str, str] = {}
        data = None
        if auth:
            headers['Authorization'] = f'Bearer {self.config.bearer_token}'
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f'{self.base_url}{path}', data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                body = resp.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode('utf-8')
                payload = json.loads(body)
                message = payload.get('error') or payload.get('errors') or body
            except Exception:
                message = str(exc)
            raise BridgeClientError(sanitize_text(str(message))) from exc
        except urllib.error.URLError as exc:
            raise BridgeClientError(f'bridge request failed: {sanitize_text(str(exc.reason))}') from exc

    def health(self) -> dict[str, Any]:
        return self._request('/health', auth=False)

    def lanes(self) -> list[dict[str, Any]]:
        payload = self._request('/lanes')
        return list(payload.get('lanes', []))

    def submit_task(self, *, lane_id: str, text: str, directory: str, session_id: str | None = None, agent: str | None = None, timeout_ms: int = 300_000) -> dict[str, Any]:
        payload = self._request(
            '/tasks',
            method='POST',
            payload={
                'lane_id': lane_id,
                'text': text,
                'directory': directory,
                'session_id': session_id,
                'agent': agent,
                'timeout_ms': timeout_ms,
            },
        )
        task = payload.get('task')
        if not isinstance(task, dict) or not task.get('task_id'):
            raise BridgeClientError('bridge response missing task payload')
        return task

    def get_task(self, task_id: str) -> dict[str, Any]:
        payload = self._request(f'/tasks/{task_id}')
        task = payload.get('task')
        if not isinstance(task, dict):
            raise BridgeClientError('bridge response missing task state')
        return task

    def submit_and_wait(
        self,
        *,
        lane_id: str,
        text: str,
        directory: str,
        session_id: str | None = None,
        agent: str | None = None,
        timeout_ms: int = 300_000,
        wait_timeout_seconds: int = 300,
        require_worker_prefix: bool = True,
        require_execution_handle: bool = True,
    ) -> dict[str, Any]:
        submitted = self.submit_task(
            lane_id=lane_id,
            text=text,
            directory=directory,
            session_id=session_id,
            agent=agent,
            timeout_ms=timeout_ms,
        )
        task_id = submitted.get('task_id')
        if not task_id:
            raise BridgeClientError('submitted task missing task_id')
        task = self.wait_for_task(str(task_id), timeout_seconds=wait_timeout_seconds)
        return self._validate_terminal_task(
            task,
            require_worker_prefix=require_worker_prefix,
            require_execution_handle=require_execution_handle,
        )

    def wait_for_task(self, task_id: str, *, timeout_seconds: int = 300) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            task = self.get_task(task_id)
            if task.get('status') in {'succeeded', 'failed', 'cancelled'}:
                return self._sanitize_terminal_task(task)
            time.sleep(self.config.poll_interval_seconds)
        raise BridgeClientError(f'timed out waiting for task {task_id}')

    def _sanitize_terminal_task(self, task: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(task)
        cleaned['summary'] = sanitize_text(str(cleaned.get('summary', '')))
        if cleaned.get('error'):
            cleaned['error'] = sanitize_text(str(cleaned['error']))
        metadata = cleaned.get('metadata')
        if isinstance(metadata, dict):
            cleaned['metadata'] = dict(metadata)
        else:
            cleaned['metadata'] = {}
        return cleaned

    def _validate_terminal_task(
        self,
        task: dict[str, Any],
        *,
        require_worker_prefix: bool,
        require_execution_handle: bool,
    ) -> dict[str, Any]:
        metadata = task.get('metadata') or {}
        if not isinstance(metadata, dict):
            raise BridgeClientError('bridge task metadata must be an object')

        status = str(task.get('status', ''))
        if status not in {'succeeded', 'failed', 'cancelled'}:
            raise BridgeClientError(f'bridge task did not reach terminal state: {status or "unknown"}')

        dispatch_status = metadata.get('dispatch_status')
        if dispatch_status not in {'completed', 'failed', 'cancelled_before_dispatch', 'cancelled_during_execution'}:
            raise BridgeClientError('bridge task missing terminal dispatch_status metadata')

        if require_execution_handle and not str(metadata.get('execution_handle', '')).strip():
            raise BridgeClientError('bridge task missing execution_handle metadata')

        if require_worker_prefix:
            worker_prefix = str(metadata.get('worker_prefix', '')).strip()
            if not worker_prefix:
                raise BridgeClientError('bridge task missing worker_prefix metadata')
            body = str(task.get('summary') or task.get('error') or '').strip()
            if body and not body.startswith(worker_prefix):
                raise BridgeClientError('bridge task output missing required worker identity prefix')

        return task
