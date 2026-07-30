from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..dependencies import AppServices, CurrentUser


router = APIRouter(prefix="/events", tags=["realtime events"])


@router.get("")
def event_stream(
    services: AppServices, current_user: CurrentUser
) -> StreamingResponse:
    del current_user
    return StreamingResponse(
        services.broker.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
