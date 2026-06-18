# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "httpx",
#   "pydantic",
#   "websockets",
# ]
# ///

import sys
import os

# Adjust python path to resolve local backend modules relative to root folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.bus import MessageBus
from backend.sandbox import WorkspaceSandbox
from backend.llm import LLMClient
from backend.agents.planner import PlannerAgent
from backend.agents.engineer import EngineerAgent
from backend.agents.reviewer import ReviewerAgent
from backend.agents.tester import TesterAgent
from backend.agents.documenter import DocumenterAgent
from backend.simulated_data import SIMULATED_SCENARIOS

app = FastAPI(title="Multi-Agent SDLC System")

# Initialize shared components
bus = MessageBus()
sandbox = WorkspaceSandbox("workspace")

# Ensure frontend directory exists
os.makedirs("frontend", exist_ok=True)

# Mount static files under /static
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def get_index():
    """Serve the dashboard UI index page."""
    return FileResponse("frontend/index.html")

@app.get("/api/history")
async def get_history():
    """Retrieve message bus history."""
    return bus.get_history()

@app.get("/api/files")
async def get_files():
    """Retrieve all files written to the workspace."""
    return sandbox.list_files()

@app.post("/api/clear")
async def clear_workspace():
    """Reset message bus and clear file workspace."""
    bus.clear()
    sandbox.clear()
    await bus.publish("system", "info", "Workspace and message bus reset complete.")
    return {"status": "success", "message": "Workspace cleared."}

class RunSimulationRequest(BaseModel):
    scenario: str

@app.post("/api/run-simulation")
async def run_simulation(data: RunSimulationRequest, background_tasks: BackgroundTasks):
    """Triggers background simulation loop to feed mockup logs & modify workspace."""
    scenario_id = data.scenario
    if scenario_id not in SIMULATED_SCENARIOS:
        return {"status": "error", "message": "Unknown simulation scenario."}
        
    background_tasks.add_task(execute_simulation_background, scenario_id)
    return {"status": "success", "message": f"Simulation '{scenario_id}' started in background."}

class RunRealRequest(BaseModel):
    request: str
    provider: str
    keys: Dict[str, str]
    cross_model_review: bool

@app.post("/api/run-real")
async def run_real(data: RunRealRequest, background_tasks: BackgroundTasks):
    """Triggers background process using real LLM API keys and physical sandbox runs."""
    background_tasks.add_task(
        execute_real_background,
        data.request,
        data.provider,
        data.keys,
        data.cross_model_review
    )
    return {"status": "success", "message": "Real agent run started in background."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket route to push real-time agent updates to dashboard."""
    await websocket.accept()
    bus.register_connection(websocket)
    try:
        # Keep connection open
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        bus.unregister_connection(websocket)

# Background execution functions

async def execute_simulation_background(scenario_id: str):
    """Simulates multi-agent execution with delays, writing mock files to workspace."""
    scenario = SIMULATED_SCENARIOS[scenario_id]
    bus.clear()
    sandbox.clear()
    
    await bus.publish("system", "info", f"Initializing Simulation Mode for scenario: '{scenario['title']}'...")
    await asyncio.sleep(1.0)
    
    for event in scenario["events"]:
        # Publish event directly to WS clients
        await bus.publish(
            sender=event["sender"],
            event_type=event["event_type"],
            message=event["message"],
            payload=event["payload"]
        )
        
        # If code is written or tests generated, write them to the physical sandbox 
        # so they populate the workspace explorer
        if event["event_type"] == "code_written" and "code" in event["payload"]:
            file_path = event["payload"]["file_path"]
            code = event["payload"]["code"]
            sandbox.write_file(file_path, code)
            
        elif event["event_type"] == "info" and "test_code" in event["payload"]:
            # Test file output
            test_file = "test_lru_cache.py" if scenario_id == "lru_cache" else ("test_auth.py" if scenario_id == "jwt_auth" else "test_rate_limiter.py")
            sandbox.write_file(test_file, event["payload"]["test_code"])
            
        elif event["event_type"] == "pr_drafted" and "pr_markdown" in event["payload"]:
            # Write PR description
            sandbox.write_file("PR_DESCRIPTION.md", event["payload"]["pr_markdown"])

        # Sleep to allow the user to watch the visualization update
        await asyncio.sleep(2.5)
        
    await bus.publish("system", "info", "Simulation completed successfully. PR is ready for merge.")

async def execute_real_background(
    request_desc: str,
    provider: str,
    keys: Dict[str, str],
    cross_model_review: bool
):
    """Runs the real multi-agent pipeline using entered credentials and real sub-shells."""
    bus.clear()
    sandbox.clear()
    
    await bus.publish("system", "info", f"Starting Real Multi-Agent Run via {provider.upper()}...")
    
    try:
        # Initialize unified LLM client
        llm = LLMClient(provider=provider, api_keys=keys)
        
        # Setup agents
        planner = PlannerAgent(llm, bus, sandbox)
        engineer = EngineerAgent(llm, bus, sandbox)
        reviewer = ReviewerAgent(llm, bus, sandbox)
        tester = TesterAgent(llm, bus, sandbox)
        documenter = DocumenterAgent(llm, bus, sandbox)
        
        # 1. Planner decomposes request
        plan = await planner.plan(request_desc)
        tasks = plan.get("tasks", [])
        test_plan = plan.get("test_plan", "Verify functionality with unit tests.")
        
        if not tasks:
            await bus.publish("system", "error", "No tasks decomposed by Planner. Terminating run.")
            return

        reviews_list = []
        test_reports_list = []
        
        # 2. Iterate through each task sequentially
        for task in tasks:
            file_path = task["file_path"]
            action = task["action"]
            
            # Subtask loops
            feedback = []
            approved = False
            max_retries = 3
            retry_count = 0
            
            original_code = ""
            try:
                original_code = sandbox.read_file(file_path)
            except Exception:
                pass
                
            code = ""
            
            # Review loop
            while not approved and retry_count < max_retries:
                # Engineer writes code
                workspace_files = sandbox.list_files()
                code = await engineer.write_code(task, workspace_files, feedback)
                
                # Determine reviewer model (implementing cross-model review)
                reviewer_model = None
                if cross_model_review:
                    # Provide simple sub-model configurations to avoid same-model biases
                    if provider == "anthropic":
                        reviewer_model = "claude-3-5-haiku" # Engineer is Sonnet, Reviewer is Haiku
                    elif provider == "openai":
                        reviewer_model = "gpt-4o-mini"      # Engineer is GPT-4o, Reviewer is mini
                    elif provider == "gemini":
                        reviewer_model = "gemini-2.5-flash" # Default override or Pro -> Flash
                
                # Reviewer critiques
                review = await reviewer.review_code(
                    task=task,
                    file_path=file_path,
                    original_code=original_code,
                    proposed_code=code,
                    reviewer_model=reviewer_model
                )
                
                reviews_list.append(review)
                
                if review.get("approved", False):
                    approved = True
                else:
                    feedback = review.get("comments", ["Code rejected by reviewer."])
                    retry_count += 1
                    await bus.publish(
                        "system",
                        "info",
                        f"Review failed. Iterating back to Engineer. Loop {retry_count}/{max_retries}."
                    )
            
            if not approved:
                await bus.publish(
                    "system",
                    "info",
                    "Warning: Code did not receive review approval, proceeding to tests anyway."
                )

            # 3. Tester generates and runs unit tests
            test_report = await tester.generate_and_run_tests(task, file_path, code, test_plan)
            test_reports_list.append(test_report)
            
            # If tests fail, allow Engineer 1 attempt to resolve/refactor the test failures
            if not test_report.get("success", False):
                await bus.publish(
                    "system",
                    "info",
                    "Tests failed. Initiating test correction refactor loop..."
                )
                
                error_feedback = [
                    "Your previous implementation failed unit tests.",
                    f"Test File: {test_report.get('test_file_path')}",
                    f"Stderr Details:\n{test_report.get('stderr')}",
                    f"Stdout Details:\n{test_report.get('stdout')}"
                ]
                
                # Engineer writes corrective code
                workspace_files = sandbox.list_files()
                code = await engineer.write_code(task, workspace_files, error_feedback)
                
                # Re-run test
                test_report = await tester.generate_and_run_tests(task, file_path, code, test_plan)
                test_reports_list.append(test_report)
                
                if test_report.get("success", False):
                    await bus.publish("system", "info", "Correction successful! Tests are now passing.")
                else:
                    await bus.publish("system", "error", "Correction failed. Tests are still failing.")
        
        # 4. Documenter compiles PR
        workspace_files = sandbox.list_files()
        pr_markdown = await documenter.draft_pr(
            plan=plan,
            implemented_files=workspace_files,
            reviews=reviews_list,
            test_reports=test_reports_list
        )
        
        await bus.publish("system", "info", "Real Agent execution finished. PR_DESCRIPTION.md has been generated.")
        
    except Exception as e:
        await bus.publish(
            "system",
            "error",
            f"An error occurred during agent execution: {str(e)}",
            {"trace": str(e)}
        )

# Main entry point for standalone run
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    reload = False if os.environ.get("PORT") else True
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)
