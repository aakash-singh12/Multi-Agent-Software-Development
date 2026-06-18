import json
import re
from backend.agents.base import BaseAgent
from typing import Dict, Any

class PlannerAgent(BaseAgent):
    def __init__(self, llm, bus, sandbox):
        super().__init__("planner", "planner", llm, bus, sandbox)

    async def plan(self, request_desc: str) -> Dict[str, Any]:
        """Analyze a user feature request and output a structured plan of tasks."""
        await self.publish(
            "planning_started",
            f"Analyzing feature request and decomposing into subtasks: '{request_desc[:60]}...'",
            {"request": request_desc}
        )

        prompt = f"Decompose the following feature request into subtasks:\n\n{request_desc}"
        
        raw_output = await self.ask_llm(prompt)
        
        # Clean potential markdown wrappers
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            plan_json = json.loads(cleaned)
            # Ensure the structure exists
            if "tasks" not in plan_json:
                plan_json["tasks"] = []
            if "test_plan" not in plan_json:
                plan_json["test_plan"] = "Verify functionality with automated unit tests."
                
            await self.publish(
                "planning_completed",
                f"Successfully decomposed request into {len(plan_json['tasks'])} tasks.",
                plan_json
            )
            return plan_json
            
        except Exception as e:
            # Fallback if JSON parsing fails
            await self.publish(
                "error",
                f"Failed to parse Planner JSON output. Falling back to simple default task.",
                {"raw_response": raw_output, "error": str(e)}
            )
            
            # Formulate a safe fallback plan
            fallback_plan = {
                "tasks": [
                    {
                        "id": "task_1",
                        "title": "Implement requested feature",
                        "description": f"Write Python code to satisfy: {request_desc}",
                        "file_path": "feature.py",
                        "action": "CREATE",
                        "dependencies": []
                    }
                ],
                "test_plan": "Implement basic unit tests to verify the feature."
            }
            
            await self.publish(
                "planning_completed",
                "Successfully generated fallback task list.",
                fallback_plan
            )
            return fallback_plan
