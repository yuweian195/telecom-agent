"""Topology loading and graph queries."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

from app.config import get_settings
from app.schemas import Topology, TopologyNode


class TopologyGraph:
    def __init__(self, topology: Topology) -> None:
        self.topology = topology
        self.nodes = {node.id: node for node in topology.nodes}
        self.children: dict[str, list[str]] = defaultdict(list)
        for edge in topology.edges:
            self.children[edge.source].append(edge.target)

    @property
    def count(self) -> int:
        return len(self.nodes)

    def node(self, node_id: str) -> TopologyNode | None:
        return self.nodes.get(node_id)

    def descendants(self, node_id: str) -> set[str]:
        seen = {node_id}
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            for child in self.children.get(current, []):
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        return seen

    def type_rank(self, node_id: str) -> int:
        node = self.nodes.get(node_id)
        if node is None:
            return 9
        return {"CORE": 0, "TRANSPORT": 1, "OLT": 2, "BASE_STATION": 3}.get(node.type, 9)


def load_topology(path: Path | None = None) -> TopologyGraph:
    target = Path(path or get_settings().topology_path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    return TopologyGraph(Topology.model_validate(payload))
