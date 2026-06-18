from backend.agents.base import BaseAgent
from typing import Dict, List, Any

class DocumenterAgent(BaseAgent):
    def __init__(self, llm, bus, sandbox):
        super().__init__("documenter", "documenter", llm, bus, sandbox)

    async def draft_pr(
        self,
        plan: Dict[str, Any],
        implemented_files: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
        test_reports: List[Dict[str, Any]]
    ) -> str:
        """Create a markdown pull request description and release notes."""
        await self.publish(
            "pr_started",
            "Compiling SDLC records and drafting Pull Request description...",
            {"plan": plan, "implemented_files": [f["path"] for f in implemented_files]}
        )

        # Build context details for the documenter
        files_summary = ""
        for f in implemented_files:
            files_summary += f"\n--- File: {f['path']} ---\n{f['content']}\n"

        review_summary = ""
        for r in reviews:
            model = r.get("reviewer_model", "default")
            approved = "Approved" if r.get("approved") else "Changes Requested"
            comments = "\n".join([f"- {c}" for c in r.get("comments", [])])
            review_summary += f"\nReview by model '{model}': Status: {approved}\nComments:\n{comments}\n"

        test_summary = ""
        for t in test_reports:
            success = "Passed" if t.get("success") else "Failed"
            test_file = t.get("test_file_path", "test_file.py")
            stderr = t.get("stderr", "")
            stdout = t.get("stdout", "")
            test_summary += f"\nTest Suite: {test_file} | Status: {success}\nOutput:\n{stdout}\n{stderr}\n"

        prompt = f"""Draft a merge-ready Pull Request description based on this SDLC history:

### Original Engineering Plan:
{plan}

### Final Code Files:
{files_summary}

### Review History:
{review_summary}

### Test Execution Reports:
{test_summary}
"""

        pr_markdown = await self.ask_llm(prompt)
        
        # Save PR description in the workspace
        self.sandbox.write_file("PR_DESCRIPTION.md", pr_markdown)

        await self.publish(
            "pr_drafted",
            "Successfully compiled and created PR_DESCRIPTION.md.",
            {"pr_markdown": pr_markdown}
        )
        return pr_markdown
