from backend.llm import LLMClient
from backend.bus import MessageBus
from backend.sandbox import WorkspaceSandbox
from typing import Dict, Any, Optional

class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        llm: LLMClient,
        bus: MessageBus,
        sandbox: WorkspaceSandbox
    ):
        self.name = name       # Human-readable name (e.g., 'planner', 'engineer')
        self.role = role       # LLM role/prompt key (e.g., 'planner', 'engineer')
        self.llm = llm
        self.bus = bus
        self.sandbox = sandbox

    async def publish(self, event_type: str, message: str, payload: Optional[Dict[str, Any]] = None):
        """Helper to publish events onto the shared message bus."""
        await self.bus.publish(self.name, event_type, message, payload)

    async def ask_llm(self, prompt: str, model_override: Optional[str] = None) -> str:
        """Call the unified LLM client with this agent's role constraints."""
        return await self.llm.generate(self.role, prompt, model_override=model_override)
