from __future__ import annotations

import json

from hermes_opencode_mcp.routing import load_route_table


def test_load_route_table(tmp_path):
    config = tmp_path / "routes.json"
    config.write_text(
        json.dumps(
            {
                "generic_topic_id": 1000,
                "routes": [
                    {
                        "topic_id": 1001,
                        "label": "coding-node-1",
                        "server_command": "python3",
                        "server_args": ["-m", "hermes_opencode_mcp"],
                        "lane_id": "coding-node-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    table = load_route_table(config)
    route = table.resolve(1001)
    assert route is not None
    assert route.server_command == "python3"
    assert route.lane_id == "coding-node-1"
