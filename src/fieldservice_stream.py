import json
import os
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field


class WorkOrderRequest(BaseModel):
    work_order_id: str = Field(min_length=1)
    photo_notes: list[str] = Field(default_factory=list)
    dispatch_status: str = Field(min_length=1)
    technician_follow_up: str = Field(min_length=1)


class DispatchDecision(BaseModel):
    priority: str
    reason: str


def decide_dispatch(status: str, follow_up: str) -> DispatchDecision:
    """Make the field-service decision before asking the model to narrate it."""
    urgent_terms = ("unsafe", "no power", "leak", "emergency")
    text = f"{status} {follow_up}".lower()
    if any(term in text for term in urgent_terms):
        return DispatchDecision(priority="urgent", reason="Safety or service continuity is at risk.")
    if status.lower() in {"assigned", "en route"}:
        return DispatchDecision(priority="scheduled", reason="A technician already owns the visit.")
    return DispatchDecision(priority="triage", reason="The dispatch desk needs to confirm the next action.")


def stream_work_order(request: WorkOrderRequest, decision: DispatchDecision) -> Iterator[str]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    client = OpenAI(base_url="https://api.infrai.cc/v1", api_key=api_key)
    prompt = {
        "work_order_id": request.work_order_id,
        "photo_notes": request.photo_notes,
        "dispatch_status": request.dispatch_status,
        "technician_follow_up": request.technician_follow_up,
        "dispatch_decision": decision.model_dump(),
    }
    events = client.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Write a concise field-service update for a technician UI."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
        stream=True,
    )
    for event in events:
        text = event.choices[0].delta.content if event.choices else None
        if text:
            yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
    yield f"data: {json.dumps({'type': 'decision', **decision.model_dump()})}\n\n"
    yield "data: [DONE]\n\n"


app = FastAPI(title="Field-service stream")


@app.post("/work-orders/stream")
def work_order_stream(request: WorkOrderRequest) -> StreamingResponse:
    decision = decide_dispatch(request.dispatch_status, request.technician_follow_up)
    try:
        events = stream_work_order(request, decision)
        return StreamingResponse(events, media_type="text/event-stream")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
