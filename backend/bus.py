import time
import inspect
from typing import Dict, List, Any, Callable, Set
import asyncio

class MessageBus:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.listeners: Set[Callable[[Dict[str, Any]], Any]] = set()
        self.connections: Set[Any] = set() # Store FastAPI WebSocket connections

    def register_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        """Register a callback for all events."""
        self.listeners.add(callback)

    def unregister_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        """Unregister a callback listener."""
        self.listeners.discard(callback)

    def register_connection(self, websocket: Any):
        """Add WebSocket connection for live broadcast."""
        self.connections.add(websocket)

    def unregister_connection(self, websocket: Any):
        """Remove WebSocket connection."""
        self.connections.discard(websocket)

    async def publish(self, sender: str, event_type: str, message: str, payload: Dict[str, Any] = None):
        """Publish an event to the bus and broadcast to all subscribers."""
        event = {
            "timestamp": time.strftime("%H:%M:%S"),
            "sender": sender, # e.g. 'planner', 'engineer', 'reviewer', 'tester', 'documenter', 'system'
            "event_type": event_type, # e.g. 'info', 'plan_created', 'code_written', 'review_result', 'test_result', 'pr_created'
            "message": message,
            "payload": payload or {}
        }
        
        self.history.append(event)
        
        # Notify Python listeners (non-blocking call)
        for listener in self.listeners:
            try:
                if inspect.iscoroutinefunction(listener):
                    asyncio.create_task(listener(event))
                else:
                    listener(event)
            except Exception as e:
                print(f"Error in bus listener: {e}")

        # Broadcast to connected WebSockets
        if self.connections:
            dead_connections = set()
            for ws in self.connections:
                try:
                    await ws.send_json(event)
                except Exception:
                    dead_connections.add(ws)
            for dead in dead_connections:
                self.connections.discard(dead)

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history

    def clear(self):
        self.history.clear()
