import json
from backend.agents.base import BaseAgent
from typing import Dict, List, Any

class EngineerAgent(BaseAgent):
    def __init__(self, llm, bus, sandbox):
        super().__init__("engineer", "engineer", llm, bus, sandbox)

    async def write_code(
        self,
        task: Dict[str, Any],
        workspace_context: List[Dict[str, Any]],
        feedback: List[str] = None
    ) -> str:
        """Write or refactor code for a subtask inside the workspace."""
        file_path = task["file_path"]
        action = task["action"]
        title = task["title"]
        desc = task["description"]

        await self.publish(
            "code_started",
            f"Writing code for task '{title}' ({file_path})...",
            {"task": task, "feedback": feedback}
        )

        # Retrieve existing content if modifying
        original_content = ""
        for file_info in workspace_context:
            if file_info["path"] == file_path:
                original_content = file_info["content"]
                break

        # Construct prompt containing context of the workspace files
        context_str = ""
        if workspace_context:
            context_str += "### Current Workspace Code Context:\n"
            for f in workspace_context:
                context_str += f"\n--- File: {f['path']} ---\n{f['content']}\n"
        else:
            context_str += "The workspace is currently empty.\n"

        prompt = f"""You are asked to perform the following task:
Task Title: {title}
Description: {desc}
File to {action}: {file_path}

{context_str}
"""

        if original_content:
            prompt += f"\n### Current Code in {file_path}:\n{original_content}\n"

        if feedback:
            prompt += f"\n### Feedback/Errors from previous run (Address all of these issues!):\n"
            for f_item in feedback:
                prompt += f"- {f_item}\n"

        prompt += "\nPlease output the updated complete file contents in a JSON object."

        raw_output = await self.ask_llm(prompt)
        
        # Clean potential markdown wrappers
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            res_json = json.loads(cleaned)
            explanation = res_json.get("explanation", "Code implemented.")
            code = res_json.get("code", "")
            
            # Write to the workspace sandbox
            saved_path = self.sandbox.write_file(file_path, code)
            
            await self.publish(
                "code_written",
                f"Completed writing code for '{file_path}'.",
                {
                    "file_path": file_path,
                    "explanation": explanation,
                    "code": code,
                    "original_code": original_content,
                    "action": action
                }
            )
            return code
            
        except Exception as e:
            # Fallback output
            await self.publish(
                "error",
                f"Failed to parse Engineer's output JSON. Writing raw response to {file_path}.",
                {"raw_response": raw_output, "error": str(e)}
            )
            
            # Fallback: try to write the raw output if we can't find a JSON
            self.sandbox.write_file(file_path, raw_output)
            
            await self.publish(
                "code_written",
                f"Completed writing fallback code to '{file_path}'.",
                {
                    "file_path": file_path,
                    "explanation": "Wrote raw output directly due to JSON parsing error.",
                    "code": raw_output,
                    "original_code": original_content,
                    "action": action
                }
            )
            return raw_output
