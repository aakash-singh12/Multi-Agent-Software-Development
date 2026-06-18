import json
from backend.agents.base import BaseAgent
from typing import Dict, Any, Optional

class ReviewerAgent(BaseAgent):
    def __init__(self, llm, bus, sandbox):
        super().__init__("reviewer", "reviewer", llm, bus, sandbox)

    async def review_code(
        self,
        task: Dict[str, Any],
        file_path: str,
        original_code: str,
        proposed_code: str,
        reviewer_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Critique the code written by the engineer, returning approval and comments."""
        model_name = reviewer_model or "default"
        await self.publish(
            "review_started",
            f"Reviewing changes in '{file_path}' (Reviewer Model: {model_name})...",
            {"task": task, "file_path": file_path, "model": model_name}
        )

        prompt = f"""Review the following code changes for task: '{task['title']}'
Description: {task['description']}
File Path: {file_path}

### Original Code:
{original_code or "[Empty File]"}

### Proposed Code:
{proposed_code}

Please analyze this code for:
1. Architectural correctness and alignment with task requirements
2. Code style, readability, and performance
3. Security vulnerabilities or edge-case crashes

Provide your evaluation in a JSON object with 'approved' and 'comments'.
"""

        raw_output = await self.ask_llm(prompt, model_override=reviewer_model)
        
        # Clean potential markdown wrappers
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            res_json = json.loads(cleaned)
            approved = res_json.get("approved", False)
            comments = res_json.get("comments", ["No comments provided."])
            
            status_msg = "Approved" if approved else "Changes Requested"
            await self.publish(
                "review_completed",
                f"Review finished: {status_msg}.",
                {
                    "approved": approved,
                    "comments": comments,
                    "reviewer_model": reviewer_model or "default"
                }
            )
            return res_json
            
        except Exception as e:
            # Fallback if reviewer fails to format JSON
            await self.publish(
                "error",
                f"Reviewer output failed to parse as JSON. Rejecting code changes by default.",
                {"raw_response": raw_output, "error": str(e)}
            )
            
            fallback_review = {
                "approved": False,
                "comments": [
                    "Failed to parse review comments format. Please structure your response as JSON.",
                    f"Raw review comments: {raw_output}"
                ]
            }
            await self.publish(
                "review_completed",
                "Review finished: Changes Requested (JSON parsing fallback).",
                fallback_review
            )
            return fallback_review
