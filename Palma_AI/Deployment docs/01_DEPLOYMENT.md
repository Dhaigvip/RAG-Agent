# FastAPI + LangChain Deployment Architecture (pyproject.toml based, uv)

This document describes the **production deployment architecture** and setup steps for a FastAPI server hosting LangChain/LangGraph based AI agents, using **pyproject.toml** and **uv** for dependency management.

---

## High-Level Architecture

[ FastAPI app ]
↓
[ ASGI server (Gunicorn + Uvicorn workers) ]
↓
[ Process manager (systemd) ]
↓
[ Linux server (VM / bare metal / cloud) ]
↓
[ Reverse proxy (Nginx, optional but recommended) ]

---

## 1. Recommended Baseline Architecture (Production)

**Operating System**
- Linux VM (Ubuntu recommended)

**Runtime**
- Python >= 3.12 (uv can provision/manage Python if needed)

**Process Model**
- uv-managed environment (no manual venv activation required)
- Gunicorn as process manager
- Uvicorn workers for ASGI

**Networking**
- Reverse proxy added later (Nginx)

---

## 2. Server Prerequisites

Update system packages:

```bash
sudo apt update
sudo apt install -y curl ca-certificates
```

Optional but recommended (native builds such as llama-cpp-python):

```bash
sudo apt install -y build-essential cmake
```

Install uv:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

Notes:

uv will create and manage the local environment automatically.

You should commit uv.lock to ensure deterministic production installs.

3. Project Structure (Recommended)

```bash
app/
├── server.py # FastAPI application
├── injestion.py
├── query.py
├── pyproject.toml
├── uv.lock
├── .env
└── logs/
```

Notes:

server.py must expose app = FastAPI(...)

.env must never be committed to source control

uv.lock should be committed for reproducible deployments

4. Dependency Management (pyproject.toml)

Your project uses PEP 621 with pyproject.toml.

Example:

```bash
[project]
name = "palma-ai"
version = "0.1.0"
description = "Palma Help Agent"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "python-dotenv",

  "langchain",
  "langgraph",
  "langchain-core>=1.2.11",
  "langchain-community>=0.4.1",
  "langchain-text-splitters>=1.1.0",
  "langchain-tavily",

  "pinecone",
  "langchain-pinecone>=0.2.13",

  "llama-cpp-python>=0.3.16",
  "langchain-ollama>=1.0.1",
]

[dependency-groups]
dev = [
  "black",
  "isort",
]
```
5. Install Dependencies with uv

From your project directory:

```bash
cd app
```

Sync dependencies (production, deterministic):

```bash
uv sync --frozen --no-dev
```

For development machines (includes dev tools):

```bash
uv sync --frozen
```

Notes:

--frozen ensures the lockfile is honored and prevents accidental upgrades.

If uv.lock does not exist yet, generate it in development:

```bash
uv sync
```
Then commit uv.lock.

6. Environment Variables

Create a .env file:

```bash
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000

OPENAI_API_KEY=xxxx
PINECONE_API_KEY=xxxx
PINECONE_ENV=xxxx

# LangChain / Ollama / Llama configuration
```

These variables are loaded via python-dotenv in your application.

Production note:

On managed platforms (ECS, etc.), prefer injecting secrets via a secrets manager rather than a local .env file.

7. Running in Production Mode

Correct production command (run via uv):

```bash
uv run gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 0.0.0.0:8000 \
  --timeout 180 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile -
```

Notes:

-w 2 is recommended for LLM-heavy workloads.

Avoid excessive workers due to API rate limits and memory usage.

Increase --timeout if your agent runs can exceed 180 seconds.

8. Running as a System Service (systemd)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/palma-ai.service
```

Service definition:

```bash
[Unit]
Description=Palma Help Agent API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/app
EnvironmentFile=/home/ubuntu/app/.env

ExecStart=/home/ubuntu/.local/bin/uv run gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 127.0.0.1:8000 \
  --timeout 180 \
  --graceful-timeout 30 \
  --keep-alive 5

Restart=always
RestartSec=3
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable palma-ai
sudo systemctl start palma-ai
sudo systemctl status palma-ai
```

Notes:

The service binds to 127.0.0.1 for security.

Public exposure and HTTPS are handled by a reverse proxy (Nginx) in later steps.

9. Verification

Test locally on the server:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```bash
{ "status": "ok" }
```