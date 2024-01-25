import asyncio
import structlog

log = structlog.get_logger(module="dispatcher")


class EventDispatcher:
    def __init__(self):
        self.listeners = {}

    def emit(self, event_name: str, *args, **kwargs):
        if event_name in self.listeners:
            log.debug(f"Emitting event {event_name}")
            for queue in self.listeners[event_name]:
                queue.put_nowait((args, kwargs))

    def listen(self, event_name: str):
        if event_name not in self.listeners:
            log.debug(f"Creating event queue for {event_name}")
            self.listeners[event_name] = set()
        queue = asyncio.Queue()
        self.listeners[event_name].add(queue)
        return queue


dispatcher = EventDispatcher()
