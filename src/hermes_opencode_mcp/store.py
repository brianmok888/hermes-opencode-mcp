from __future__ import annotations

from dataclasses import replace

from .models import LaneProfile, TaskRecord, utc_now


class InMemoryStore:
    def __init__(self, lane_profiles: dict[str, LaneProfile]) -> None:
        self._lanes = dict(lane_profiles)
        self._tasks: dict[str, TaskRecord] = {}

    def lanes(self) -> list[LaneProfile]:
        return list(self._lanes.values())

    def get_lane(self, lane_id: str) -> LaneProfile | None:
        return self._lanes.get(lane_id)

    def set_lane_state(self, lane_id: str, state: str, error: str | None = None) -> LaneProfile:
        lane = self._lanes[lane_id]
        updated = replace(lane, state=state, last_error=error, updated_at=utc_now())
        self._lanes[lane_id] = updated
        return updated

    def add_task(self, task: TaskRecord) -> None:
        self._tasks[task.task_id] = task

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def save_task(self, task: TaskRecord) -> None:
        self._tasks[task.task_id] = task

    def request_cancel(self, task_id: str) -> TaskRecord | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if task.status in {"succeeded", "failed", "cancelled"}:
            return task
        updated = replace(task, cancel_requested=True)
        self._tasks[task_id] = updated
        return updated
