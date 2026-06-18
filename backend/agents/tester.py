import json
import os
from backend.agents.base import BaseAgent
from typing import Dict, Any

class TesterAgent(BaseAgent):
    def __init__(self, llm, bus, sandbox):
        super().__init__("tester", "tester", llm, bus, sandbox)

    async def generate_and_run_tests(
        self,
        task: Dict[str, Any],
        file_path: str,
        implemented_code: str,
        test_plan: str
    ) -> Dict[str, Any]:
        """Generate unit tests, write them, execute them, and report results."""
        # Derive test file name, e.g. "test_lru_cache.py" for "lru_cache.py"
        base_name = os.path.basename(file_path)
        name_part, _ = os.path.splitext(base_name)
        test_file_path = f"test_{name_part}.py"

        await self.publish(
            "test_started",
            f"Generating and running tests in '{test_file_path}' to verify '{file_path}'...",
            {"task": task, "file_path": file_path, "test_file_path": test_file_path, "test_plan": test_plan}
        )

        prompt = f"""Generate Python unit tests for the following implemented code:
File to test: {file_path}
Test plan: {test_plan}

### Implemented Code in {file_path}:
{implemented_code}

Generate a complete, runnable test script using Python's standard 'unittest' framework.
The tests should import components from the file correctly (e.g. `from {name_part} import ...` or `import {name_part}`).
Output the complete test code in a JSON object.
"""

        raw_output = await self.ask_llm(prompt)
        
        # Clean potential markdown wrappers
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            res_json = json.loads(cleaned)
            test_explanation = res_json.get("explanation", "Test suite generated.")
            test_code = res_json.get("code", "")
            
            # Write test file
            self.sandbox.write_file(test_file_path, test_code)
            
            await self.publish(
                "info",
                f"Wrote test suite to '{test_file_path}'. Executing tests...",
                {"test_code": test_code}
            )
            
            # Run the test suite
            test_result = self.sandbox.execute_test(test_file_path)
            
            success = test_result["success"]
            status_msg = "Passed" if success else "Failed"
            
            await self.publish(
                "test_completed",
                f"Test execution finished: {status_msg}.",
                {
                    "success": success,
                    "test_file_path": test_file_path,
                    "stdout": test_result["stdout"],
                    "stderr": test_result["stderr"],
                    "exit_code": test_result["exit_code"],
                    "test_explanation": test_explanation
                }
            )
            return {
                "success": success,
                "test_file_path": test_file_path,
                "test_code": test_code,
                "stdout": test_result["stdout"],
                "stderr": test_result["stderr"]
            }

        except Exception as e:
            # Fallback if generation or execution completely crash
            fail_msg = f"Failed to generate or run tests: {str(e)}"
            await self.publish(
                "test_completed",
                f"Test execution failed: Error during generation/execution.",
                {"success": False, "stderr": fail_msg, "stdout": "", "exit_code": -4}
            )
            return {
                "success": False,
                "test_file_path": test_file_path,
                "test_code": "",
                "stdout": "",
                "stderr": fail_msg
            }
