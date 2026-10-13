from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, Field

from companion.bus import bus
from companion.events import TranscriptEvent

router = APIRouter(prefix="/api")


def _db(request: Request):
    return request.app.state.db


# ---------- settings ----------
class SettingBody(BaseModel):
    value: str


@router.get("/settings")
async def get_settings(request: Request):
    return await _db(request).get_settings()


@router.put("/settings/{key}")
async def put_setting(key: str, body: SettingBody, request: Request):
    await _db(request).set_setting(key, body.value)
    return {"key": key, "value": body.value}


# ---------- chat history (text fallback) ----------
class ChatIn(BaseModel):
    text: str = Field(min_length=1)
    session_id: str = "default"


@router.get("/messages")
async def list_messages(request: Request, limit: int = 50, session_id: str | None = None):
    return await _db(request).recent_messages(min(limit, 200), session_id)


@router.post("/messages")
async def post_message(body: ChatIn, request: Request):
    # Phase 3 will route this to the LLM; for now it only stores and broadcasts.
    msg_id = await _db(request).add_message(body.session_id, "user", body.text, "text")
    bus.publish(TranscriptEvent(role="user", text=body.text, final=True))
    return {"id": msg_id}


# ---------- reminders ----------
class ReminderIn(BaseModel):
    text: str = Field(min_length=1)
    due_at: AwareDatetime  # must include a timezone, e.g. 2026-10-14T06:00:00+01:00
    urgency: Literal["low", "normal", "high"] = "normal"


class ReminderPatch(BaseModel):
    status: Literal["pending", "fired", "done", "cancelled"]


@router.get("/reminders")
async def list_reminders(request: Request, status: str | None = None):
    return await _db(request).list_reminders(status)


@router.post("/reminders", status_code=201)
async def create_reminder(body: ReminderIn, request: Request):
    rid = await _db(request).add_reminder(body.text, body.due_at, body.urgency)
    return {"id": rid}


@router.patch("/reminders/{reminder_id}")
async def patch_reminder(reminder_id: int, body: ReminderPatch, request: Request):
    if not await _db(request).set_reminder_status(reminder_id, body.status):
        raise HTTPException(404, "Reminder not found")
    return {"id": reminder_id, "status": body.status}


# ---------- facts and affect ----------
class FactIn(BaseModel):
    subject: str
    relation: str
    object: str


@router.get("/facts")
async def list_facts(request: Request, subject: str | None = None):
    return await _db(request).list_facts(subject)


@router.post("/facts", status_code=201)
async def add_fact(body: FactIn, request: Request):
    await _db(request).add_fact(body.subject, body.relation, body.object)
    return {"ok": True}


@router.get("/affect")
async def recent_affect(request: Request, limit: int = 100):
    return await _db(request).recent_affect(min(limit, 500))