from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class WorkflowTemplateNode:
    """그림 안 노드 (작업 스펙)."""

    slot_key: str  # 그림 안에서 고유한 키 (예: "n_1", "n_abc")
    title: str
    description: str = ""
    assignee_agent_id: str | None = None  # 실제 에이전트 profile id (있으면)
    template_key: str | None = None  # 또는 기본 제공 에이전트 templateKey (예: "coder")
    position_x: float = 0
    position_y: float = 0


@dataclass(slots=True)
class WorkflowTemplateEdge:
    """그림 안 화살표 (source slot → target slot 의 blocks 관계)."""

    source_slot_key: str
    target_slot_key: str


@dataclass(slots=True)
class WorkflowTemplateGraph:
    nodes: list[WorkflowTemplateNode] = field(default_factory=list)
    edges: list[WorkflowTemplateEdge] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "slotKey": node.slot_key,
                    "title": node.title,
                    "description": node.description,
                    "assigneeAgentId": node.assignee_agent_id,
                    "templateKey": node.template_key,
                    "positionX": node.position_x,
                    "positionY": node.position_y,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "sourceSlotKey": edge.source_slot_key,
                    "targetSlotKey": edge.target_slot_key,
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> "WorkflowTemplateGraph":
        nodes_raw = payload.get("nodes") if isinstance(payload, dict) else None
        edges_raw = payload.get("edges") if isinstance(payload, dict) else None
        nodes: list[WorkflowTemplateNode] = []
        edges: list[WorkflowTemplateEdge] = []
        if isinstance(nodes_raw, list):
            for item in nodes_raw:
                if not isinstance(item, dict):
                    continue
                slot_key = str(item.get("slotKey") or "").strip()
                title = str(item.get("title") or "").strip()
                if not slot_key or not title:
                    continue
                nodes.append(
                    WorkflowTemplateNode(
                        slot_key=slot_key,
                        title=title,
                        description=str(item.get("description") or ""),
                        assignee_agent_id=_optional_str(item.get("assigneeAgentId")),
                        template_key=_optional_str(item.get("templateKey")),
                        position_x=float(item.get("positionX") or 0),
                        position_y=float(item.get("positionY") or 0),
                    )
                )
        if isinstance(edges_raw, list):
            for item in edges_raw:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("sourceSlotKey") or "").strip()
                target = str(item.get("targetSlotKey") or "").strip()
                if not source or not target or source == target:
                    continue
                edges.append(WorkflowTemplateEdge(source_slot_key=source, target_slot_key=target))
        return cls(nodes=nodes, edges=edges)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class WorkflowTemplate:
    template_id: str
    owner_key: str
    owner_user_id: int | None
    name: str
    description: str
    graph: WorkflowTemplateGraph
    created_at: datetime | None = None
    updated_at: datetime | None = None
