# ADVOCATE: Autonomous Multi-Agent SDLC System

ADVOCATE is a multi-agent software development lifecycle (SDLC) system where specialized AI agents collaborate autonomously to plan, code, critique, test, and release feature requests. 

The system features a real-time, glassmorphic developer dashboard to configure, launch, and monitor agent handoffs, inspect file trees, analyze live code diffs, read sandboxed test output, and view pull requests.

---

## System Architecture

```mermaid
graph TD
    User([User Request]) --> Planner[Planner Agent]
    Planner -->|Decomposes Plan| Bus[Shared Message Bus]
    Bus -->|Tasks Routing| Engineer[Engineer Agent]
    Engineer -->|Wrote Code| Reviewer[Reviewer Agent]
    
    Reviewer -->|Critiques Code| Decision1{Approved?}
    Decision1 -->|No: Feedback Loop| Engineer
    Decision1 -->|Yes| Tester[Tester Agent]
    
    Tester -->|Runs Unit Tests| Decision2{Passed?}
    Decision2 -->|No: Error Correction| Engineer
    Decision2 -->|Yes| Documenter[Documenter Agent]
    
    Documenter -->|PR Summary| Output([Merge-ready PR])
```

### Core Agents

1. **Planner Agent**: Analyzes user requests, identifies dependency trees, determines file creation/modification routes, and outputs a structured JSON engineering plan.
2. **Engineer Agent**: Writes and refactors code inside the workspace sandbox, reacting to instructions and refactoring code iteratively when reviews or tests fail.
3. **Reviewer Agent**: Critiques implementations for architectural soundness, performance, style, and security, approving or request changes. Supports **Cross-Model Review** to reduce same-model cognitive bias (e.g., Anthropic Claude Haiku reviewing Claude Sonnet's output).
4. **Tester Agent**: Generates testing suites using Python's standard `unittest` framework, executes runs dynamically in a sub-process, and reports pass/fail logs.
5. **Documenter/Release Agent**: Gathers SDLC execution logs, code implementations, code reviews, and test reports to output a markdown Pull Request description and changelog.

### Shared Message Bus

Agents publish and consume messages using a central, event-driven `MessageBus`. This maintains state and coordinates routing. Events are pushed live to the web dashboard via WebSockets.

---

## File Structure

```text
e:/lablab project-1/
├── backend/
│   ├── agents/
│   │   ├── base.py          # Unified base agent class
│   │   ├── planner.py       # Planner Agent
│   │   ├── engineer.py      # Engineer Agent
│   │   ├── reviewer.py      # Reviewer Agent
│   │   ├── tester.py        # Tester Agent
│   │   └── documenter.py    # Documenter Agent
│   ├── bus.py               # Shared Event Message Bus
│   ├── llm.py               # Unified API Client (Claude, OpenAI, Gemini)
│   ├── main.py              # FastAPI server & route orchestration
│   ├── sandbox.py           # Sandboxed file/process manager
│   └── simulated_data.py    # Simulated logs & events for Demo Mode
├── frontend/
│   ├── index.html           # Glassmorphic developer dashboard
│   ├── styles.css           # Custom styles, animations & diff themes
│   └── app.js               # Websocket bindings & UI interactive logic
├── workspace/               # Sandboxed directory where agents write files & tests
├── run.bat                  # Windows startup batch command
└── README.md                # System documentation
```

---

## Getting Started

### Prerequisites

You need the `uv` package manager installed. If not available on your path, install it using the system instructions. (Our IDE automatically sets up and maps `uv` locally).

### Running Locally

1. Start the server using the batch script:
   ```bash
   run.bat
   ```
   *Alternatively, run:*
   ```bash
   uv run backend/main.py
   ```

2. Open your web browser and navigate to:
   [http://localhost:8000](http://localhost:8000)

3. **Demo Mode (Out of the Box)**:
   Choose one of the pre-loaded developer scenarios (e.g., *Thread-Safe LRU Cache*, *Token Bucket Limiter*, or *JWT Authorization*) under **OR RUN BUILT-IN DEMO** to watch the multi-agent system collaborate in real time with high-fidelity logs, workspace updates, and test executions.

4. **Real Mode (Autonomous Execution)**:
   - Click the **Keys** button in the header and input your API credentials (e.g., Anthropic API Key).
   - Enter your prompt in the command center text field (e.g., *"Create an email validator with unit tests"*).
   - Select your LLM backbone (e.g., Anthropic or OpenAI) and click **Run Orchestration**.
   - Watch the agents dynamically write files and run real test suites inside `./workspace/`!
