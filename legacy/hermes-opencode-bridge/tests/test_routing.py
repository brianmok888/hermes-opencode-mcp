import json
from pathlib import Path

import pytest

from hermes_opencode_bridge.routing import RouteConfigError, load_route_table


def test_load_route_table_success(tmp_path: Path) -> None:
    path = tmp_path / 'routes.json'
    path.write_text(json.dumps({
        'generic_topic_id': 555,
        'routes': [
            {
                'topic_id': 3,
                'label': 'coding-node',
                'bridge_url': 'http://127.0.0.1:18097',
                'secret_env': 'HERMES_BRIDGE_VM02_TOKEN',
                'lane_id': 'coding-node-1',
            }
        ],
    }), encoding='utf-8')
    table = load_route_table(path)
    assert table.generic_topic_id == 555
    route = table.resolve(3)
    assert route is not None
    assert route.lane_id == 'coding-node-1'


def test_load_route_table_requires_routes(tmp_path: Path) -> None:
    path = tmp_path / 'routes.json'
    path.write_text(json.dumps({'generic_topic_id': 555, 'routes': []}), encoding='utf-8')
    with pytest.raises(RouteConfigError):
        load_route_table(path)
