"""
Project Nexus

Event System

Every important action inside Nexus
can become an event.
"""


class Event:

    def __init__(self, name: str):

        self.name = name


class EventManager:

    def __init__(self):

        self.events = {}

    def register(self, event_name: str, callback):

        self.events.setdefault(event_name, []).append(callback)

    async def emit(self, event_name: str, *args, **kwargs):

        if event_name not in self.events:
            return

        for callback in self.events[event_name]:
            await callback(*args, **kwargs)


events = EventManager()
