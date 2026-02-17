# FastAPI + LangChain Deployment Architecture (pyproject.toml based)

This document describes the **production deployment architecture** and setup steps for a FastAPI server hosting LangChain-based AI agents, using **pyproject.toml** for dependency management.

---

## High-Level Architecture


[ FastAPI app ]
↓
[ ASGI server (Uvicorn / Gunicorn) ]
↓
[ Process manager ]
↓
[ Linux server (VM / bare metal / cloud) ]


---

## 1. Recommended Baseline Architecture (Production)

**Operating System**
- Linux VM (Ubuntu recommended)

**Runtime**
- Python >= 3.12

**Process Model**
- Python virtual environment
- Gunicorn as process manager
- Uvicorn workers for ASGI

**Networking**
- Reverse proxy added later (Nginx)

---

## 2. Server Prerequisites

Update system packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

Optional but recommended (native builds such as llama-cpp-python):

sudo apt install -y build-essential cmake
3. Project Structure (Recommended)
app/
├── server.py          # FastAPI application
├── injestion.py
├── query.py
├── pyproject.toml
├── .env
└── logs/

Notes:

server.py must expose app = FastAPI(...)

.env must never be committed to source control

4. Dependency Management (pyproject.toml)

Your project uses PEP 621 with pyproject.toml.

pyproject.toml (example)
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
5. Python Virtual Environment

Create and activate a virtual environment:

cd app
python3 -m venv venv
source venv/bin/activate

Upgrade pip:

pip install --upgrade pip

Install dependencies from pyproject.toml:

pip install .

For development dependencies:

pip install .[dev]
6. Environment Variables

Create a .env file:

UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000

OPENAI_API_KEY=xxxx
PINECONE_API_KEY=xxxx
PINECONE_ENV=xxxx

# LangChain / Ollama / Llama configuration

These variables are loaded via python-dotenv.

7. Running in Production Mode

Correct Production Command
Use Gunicorn with Uvicorn workers:

gunicorn \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 0.0.0.0:8000 \
  server:app

Notes:

-w 2 is recommended for LLM-heavy workloads

Avoid excessive workers due to API rate limits and memory usage

8. Running as a System Service (systemd)

Create a systemd service file:

sudo nano /etc/systemd/system/palma-ai.service
Service Definition
[Unit]
Description=Palma Help Agent API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/app
EnvironmentFile=/home/ubuntu/app/.env
ExecStart=/home/ubuntu/app/venv/bin/gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 2 \
    -b 127.0.0.1:8000 \
    server:app
Restart=always
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target

Enable and start the service:

sudo systemctl daemon-reload
sudo systemctl enable palma-ai
sudo systemctl start palma-ai
sudo systemctl status palma-ai
9. Verification

Test locally on the server:

curl http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok"
}
Notes

The API binds to 127.0.0.1 for security

Public exposure and HTTPS are handled by a reverse proxy (Nginx) in later steps

This setup is optimized for LangChain, Pinecone, and LLM workloads

Python 3.12 is required