from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.contracts.task.task_response import TaskRunResponse
from app.domain.orchestration.contracts import OrchestrationRequest

router = APIRouter(prefix="/flows", tags=["flows"])


class ExecuteFlowRequest(BaseModel):
    owner_key: str = "local-user"
    input_payload: dict[str, Any] = Field(default_factory=dict)


@router.get("", response_model=list[str])
def list_flows(request: Request) -> list[str]:
    return request.app.state.orchestrator.list_flows()


@router.post("/{flow_name}/execute", response_model=TaskRunResponse)
async def execute_flow(flow_name: str, payload: ExecuteFlowRequest, request: Request) -> TaskRunResponse:
    try:
        task = await request.app.state.orchestrator.start(
            OrchestrationRequest(
                owner_key=payload.owner_key,
                input_payload=payload.input_payload,
                requested_route=flow_name,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown flow: {error.args[0]}") from error
    return TaskRunResponse.model_validate(task, from_attributes=True)
