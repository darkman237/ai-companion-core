import asyncio
from pydantic import BaseModel


class EventBus:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[str]] = set()

    def subscribe(self, maxsize: int = 100) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subs.discard(q)

    def publish(self, event: BaseModel) -> None:
        payload = event.model_dump_json()
        for q in list(self._subs):
            if q.full():  # slow client: drop the oldest event, never block the pipeline
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(payload)


bus = EventBus()