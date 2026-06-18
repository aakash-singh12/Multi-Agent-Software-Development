import os
import json
import httpx
import asyncio
from typing import Dict, List, Any, Optional

# System Prompts for specialized SDLC agents

PLANNER_SYSTEM = """You are the Lead Software Architect and Planner Agent.
Your job is to take a feature request or bug report and decompose it into a structured, step-by-step engineering plan.
Analyze the request, determine which files need to be created, modified, or deleted, and output a structured JSON plan.

You must output valid JSON ONLY, using the following schema:
{
  "tasks": [
    {
      "id": "task_1",
      "title": "Create database model",
      "description": "Create the user database schema with fields for email, password hash, and created_at.",
      "file_path": "models.py",
      "action": "CREATE",
      "dependencies": []
    },
    {
      "id": "task_2",
      "title": "Implement signup endpoint",
      "description": "Add a signup route that hashes passwords and saves the user record.",
      "file_path": "auth.py",
      "action": "MODIFY",
      "dependencies": ["task_1"]
    }
  ],
  "test_plan": "Write unit tests in test_auth.py to verify password hashing and user saving, including duplicate email cases."
}
Do not write any text before or after the JSON object.
"""

ENGINEER_SYSTEM = """You are the Senior Software Engineer Agent.
Your job is to write or refactor code to implement a specific subtask.
You will be given:
1. The subtask description
2. The context of existing files (if any)
3. Any feedback from previous reviews (if the code was rejected)

You must output a structured JSON object containing your explanation and the complete new/updated code for the file:
{
  "explanation": "Briefly describe your design decisions and implementation details.",
  "code": "The complete source code of the file. Do not include markdown code block backticks in this field."
}
Only output the JSON object.
"""

REVIEWER_SYSTEM = """You are the QA Lead and Reviewer Agent.
Your job is to critique the code written by the Engineer Agent.
Analyze the task, the original code, and the new proposed code.
Verify correctness, security (avoid vulnerabilities), performance, readability, and testability.

You must output a structured JSON object:
{
  "approved": true or false,
  "comments": [
    "List specific code issues, formatting suggestions, or architectural flaws. If approved, list minor suggestions or write a brief congratulatory note."
  ]
}
Only output the JSON object.
"""

TESTER_SYSTEM = """You are the Test Automation Engineer Agent.
Your job is to write high-quality unit/integration tests to verify the new implementation.
You will write python unit tests using the standard 'unittest' framework.
You will be given the task, the implemented code, and the test plan.

Output a structured JSON object containing the complete test code:
{
  "explanation": "Briefly describe the test cases covered.",
  "code": "The complete test script using python's unittest. Do not include markdown code block backticks in this field."
}
Only output the JSON object.
"""

DOCUMENTER_SYSTEM = """You are the Technical Writer and Release Engineer Agent.
Your job is to write a comprehensive pull request description and release notes.
You will be given the full engineering plan, the final implemented files, the review comments, and the test reports.

Format your output as a markdown document with:
1. PR Title (short and clear)
2. Description of changes
3. Files modified/created table
4. Automated Test Summary (include test coverage details and status)
5. Review summary (including who reviewed it and key feedback addressed)
6. Changelog entry

Do not wrap the markdown inside JSON; just output raw markdown content.
"""

SYSTEM_PROMPTS = {
    "planner": PLANNER_SYSTEM,
    "engineer": ENGINEER_SYSTEM,
    "reviewer": REVIEWER_SYSTEM,
    "tester": TESTER_SYSTEM,
    "documenter": DOCUMENTER_SYSTEM
}

class LLMClient:
    def __init__(self, provider: str = "simulation", api_keys: Optional[Dict[str, str]] = None):
        self.provider = provider.lower()
        self.api_keys = api_keys or {}
        
    def get_api_key(self, key_name: str) -> str:
        # Check passed keys first, then environment variables
        return self.api_keys.get(key_name) or os.environ.get(key_name, "")

    async def generate(self, role: str, prompt: str, model_override: Optional[str] = None) -> str:
        system_prompt = SYSTEM_PROMPTS.get(role, "")
        
        if self.provider == "simulation":
            # Simulation mode - we return realistic wait times and mock responses
            await asyncio.sleep(2.0)
            return await self._get_simulated_response(role, prompt)

        # Real Mode API calls
        async with httpx.AsyncClient(timeout=60.0) as client:
            if self.provider == "anthropic":
                api_key = self.get_api_key("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("Anthropic API key missing. Please provide ANTHROPIC_API_KEY.")
                
                model = model_override or "claude-3-5-sonnet-20241022"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                data = {
                    "model": model,
                    "max_tokens": 4000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}]
                }
                response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
                response.raise_for_status()
                res_json = response.json()
                return res_json["content"][0]["text"]

            elif self.provider == "openai":
                api_key = self.get_api_key("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API key missing. Please provide OPENAI_API_KEY.")
                
                model = model_override or "gpt-4o"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                }
                # Request JSON output for agents that require JSON
                if role in ["planner", "engineer", "reviewer", "tester"]:
                    data["response_format"] = {"type": "json_object"}
                    
                response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
                response.raise_for_status()
                res_json = response.json()
                return res_json["choices"][0]["message"]["content"]

            elif self.provider == "gemini":
                api_key = self.get_api_key("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("Gemini API key missing. Please provide GEMINI_API_KEY.")
                
                model = model_override or "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                
                full_prompt = f"{system_prompt}\n\nUser Input/Context:\n{prompt}"
                data = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }]
                }
                
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                res_json = response.json()
                text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                # Clean markdown JSON block formatting if present
                if text.strip().startswith("```json"):
                    text = text.strip().split("```json")[1].split("```")[0].strip()
                elif text.strip().startswith("```"):
                    text = text.strip().split("```")[1].split("```")[0].strip()
                return text

            else:
                raise ValueError(f"Unknown provider: {self.provider}")

    async def _get_simulated_response(self, role: str, prompt: str) -> str:
        # Fallback simulation logs if not querying a scenario from simulated_data
        # We parse the prompt briefly to see if it matches pre-canned flows
        if role == "planner":
            return json.dumps({
                "tasks": [
                    {
                        "id": "task_1",
                        "title": "Implement LRU Cache",
                        "description": "Write a thread-safe LRU Cache in Python with get and put methods.",
                        "file_path": "lru_cache.py",
                        "action": "CREATE",
                        "dependencies": []
                    }
                ],
                "test_plan": "Write unit tests in test_lru_cache.py testing cache eviction, updates, and key updates."
            })
        elif role == "engineer":
            return json.dumps({
                "explanation": "Implemented standard LRU cache using an Ordered Dict for O(1) time complexity.",
                "code": "from collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.cache = OrderedDict()\n        self.capacity = capacity\n\n    def get(self, key: int) -> int:\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n\n    def put(self, key: int, value: int) -> None:\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)\n"
            })
        elif role == "reviewer":
            return json.dumps({
                "approved": True,
                "comments": ["Excellent design using collections.OrderedDict. O(1) operations are satisfied."]
            })
        elif role == "tester":
            return json.dumps({
                "explanation": "Added basic unit tests for cache hits, misses, and eviction.",
                "code": "import unittest\nfrom lru_cache import LRUCache\n\nclass TestLRUCache(unittest.TestCase):\n    def test_cache_operations(self):\n        cache = LRUCache(2)\n        cache.put(1, 1)\n        cache.put(2, 2)\n        self.assertEqual(cache.get(1), 1)\n        cache.put(3, 3) # evicts key 2\n        self.assertEqual(cache.get(2), -1)\n        cache.put(4, 4) # evicts key 1\n        self.assertEqual(cache.get(1), -1)\n        self.assertEqual(cache.get(3), 3)\n        self.assertEqual(cache.get(4), 4)\n\nif __name__ == '__main__':\n    unittest.main()\n"
            })
        elif role == "documenter":
            return """# PR: Implement LRU Cache

## Description
This PR implements a standard, efficient Least Recently Used (LRU) Cache utilizing `collections.OrderedDict`.

## Files Created
- `lru_cache.py` (New class `LRUCache`)

## Verification Summary
- Passing unit tests in `test_lru_cache.py` verifying get, put, and eviction limits.
"""
        return "Simulation response"
