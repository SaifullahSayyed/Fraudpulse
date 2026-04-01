import asyncio
import json
from typing import AsyncGenerator

class SSEManager:
    
    def __init__(self):
        self.subscribers: list[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        try:
            yield "data: {\"status\": \"connected\"}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            self.subscribers.remove(queue)

    def publish(self, event_data: dict):
        
        msg = json.dumps(event_data)
        for queue in self.subscribers:
            queue.put_nowait(msg)

sse_manager = SSEManager()