from __future__ import annotations

from pydantic import BaseModel


class GatewaySubscriptionResponse(BaseModel):
    type: str = "subscribed"
    task_run_id: str
