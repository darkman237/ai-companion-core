import asyncio
import os
from contextlib import asynccontextmanager, suppress

from companion.api.routes import router
from companion.memory.db import Database

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from companion.bus import bus
from companion.events import AffectEvent, VoiceState, VoiceStateEvent


async def _demo_loop() -> None:
    """Dev only: cycles fake events so the UI has something to render."""
    states = list(VoiceState)
    i = 0
    while True:
        bus.publish(VoiceStateEvent(state=states[i % len(states)]))
        if i % 3 == 0:
            bus.publish(AffectEvent(sadness=0.2, anxiety=0.1, valence=0.3, s_distress=0.15))
        i += 1
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database()
    await db.connect()
    app.state.db = db
    task = asyncio.create_task(_demo_loop()) if os.getenv("COMPANION_DEMO") == "1" else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    await db.close()


app = FastAPI(title="Companion API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()
    q = bus.subscribe()
    try:
        while True:
            await ws.send_text(await q.get())
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(q)