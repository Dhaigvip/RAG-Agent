# From C:\src\AI\Palma AI
.\.venv\Scripts\Activate.ps1

# Option 1: via uvicorn (recommended)
uv run uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Option 2: via Python (also fine)
python server.py


Expose on your network
uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload

.\.venv\Scripts\Activate.ps1
& .\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload --log-level debug