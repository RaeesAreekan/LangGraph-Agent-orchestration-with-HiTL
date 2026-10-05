# LangGraph Multi-Agent Orchestrator

A proof of concept for durable multi-agent workflows built with LangGraph.

## Flow overview

A client submits a task through FastAPI. The executor runs it in-process or queues it through Celery and Redis. The workflow then:

```text
Task
  ↓
Supervisor creates a plan
  ↓
Research and analysis specialists run
  ↓
Reviewer evaluates results
  ├── revise specialists
  ├── request human approval
  ├── escalate
  └── synthesize final answer
```

Tasks, events, and LangGraph checkpoints are persisted in PostgreSQL. Brave Search is available through MCP, and ChromaDB provides optional conversational memory.

Detailed flow: [mermaid-diagram.mmd](mermaid-diagram.mmd)

## Run locally

Requirements:

- Python 3.10+
- Docker Desktop
- Node.js/npm when using Brave MCP
- OpenAI API key for live agents or embeddings
- Brave Search API key when using Brave MCP

Create the environment:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start PostgreSQL, Redis, and ChromaDB:

```powershell
docker run --name agent-orchestrator-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=orchestrator `
  -p 5432:5432 `
  -d postgres:16

docker run --name agent-orchestrator-redis `
  -p 6379:6379 `
  -d redis:7

docker volume create agent-orchestrator-chroma-data

docker run --name agent-orchestrator-chroma `
  -p 8001:8000 `
  -v agent-orchestrator-chroma-data:/data `
  -d chromadb/chroma
```

If these containers already exist:

```powershell
docker start agent-orchestrator-postgres agent-orchestrator-redis agent-orchestrator-chroma
```

Create a `.env` file in the project root.

For a fast local test:

```dotenv
AGENT_MODE=fake
TOOL_MODE=demo
CHECKPOINT_BACKEND=memory
EXECUTION_BACKEND=in_process
MEMORY_ENABLED=false
```

For the persistent live setup:

```dotenv
AGENT_MODE=live
TOOL_MODE=mcp
CHECKPOINT_BACKEND=postgres
EXECUTION_BACKEND=celery

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/orchestrator
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-key
BRAVE_API_KEY=your-brave-key

MEMORY_ENABLED=true
MEMORY_BACKEND=chroma
CHROMA_URL=http://localhost:8001
```

Never commit `.env` or expose API keys.

Start the API:

```powershell
uvicorn app.main:create_app --factory --reload
```

When `EXECUTION_BACKEND=celery`, start a second terminal for the worker:

```powershell
.\.venv\Scripts\celery.exe `
  -A app.execution.celery_tasks:celery_app `
  worker `
  --loglevel=INFO `
  --pool=solo
```

The API runs at `http://127.0.0.1:8000`. Run tests with:

```powershell
.\.venv\Scripts\pytest.exe -q
```
