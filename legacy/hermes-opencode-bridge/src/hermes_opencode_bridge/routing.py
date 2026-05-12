from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class RouteConfigError(RuntimeError):
    pass


@dataclass(slots=True)
class TopicRoute:
    topic_id: int
    label: str
    bridge_url: str
    secret_env: str
    lane_id: str
    mode: str = 'opencode'


@dataclass(slots=True)
class RouteTable:
    generic_topic_id: int
    routes: dict[int, TopicRoute]

    def resolve(self, topic_id: int | None) -> TopicRoute | None:
        if topic_id is None:
            return None
        return self.routes.get(int(topic_id))


def load_route_table(path: str | Path) -> RouteTable:
    config_path = Path(path).expanduser()
    if not config_path.exists():
        raise RouteConfigError(f'route config not found: {config_path}')
    try:
        raw = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise RouteConfigError(f'invalid route config json: {config_path}') from exc
    if not isinstance(raw, dict):
        raise RouteConfigError('route config must be a json object')
    generic_topic_id = int(raw.get('generic_topic_id', 0))
    raw_routes = raw.get('routes')
    if not isinstance(raw_routes, list) or not raw_routes:
        raise RouteConfigError('route config requires a non-empty routes list')
    routes: dict[int, TopicRoute] = {}
    for item in raw_routes:
        if not isinstance(item, dict):
            raise RouteConfigError('each route must be a json object')
        route = TopicRoute(
            topic_id=int(item['topic_id']),
            label=str(item['label']).strip(),
            bridge_url=str(item['bridge_url']).strip(),
            secret_env=str(item['secret_env']).strip(),
            lane_id=str(item['lane_id']).strip(),
            mode=str(item.get('mode', 'opencode')).strip() or 'opencode',
        )
        if not route.label or not route.bridge_url or not route.secret_env or not route.lane_id:
            raise RouteConfigError('route entries require label, bridge_url, secret_env, and lane_id')
        routes[route.topic_id] = route
    return RouteTable(generic_topic_id=generic_topic_id, routes=routes)
