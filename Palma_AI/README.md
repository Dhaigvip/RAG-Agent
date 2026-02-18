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

## Notes

- If port 8000 is already in use, run on 8001:
	uv run uvicorn server:app --host 127.0.0.1 --port 8001 --reload

- Health check (adjust port if needed):
	curl http://127.0.0.1:8000/health

## Environment Setup

Create a `.env` file in this folder with the following keys:

```env
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_pinecone_index_name
TAVILY_API_KEY=your_tavily_api_key
```

The `/chat` and ingestion endpoints require these. You can verify Pinecone with:

```powershell
uv run python verify_pinecone.py
```