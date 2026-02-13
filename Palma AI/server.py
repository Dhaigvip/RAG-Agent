import asyncio
import time
import os
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware


from typing import Literal, Optional, Dict
from uuid import uuid4
from urllib.parse import unquote
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from injestion import run_pipeline
from query import query_app


load_dotenv()

app = FastAPI(title="Palma Help Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],        # Allows OPTIONS, POST, etc
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    url: HttpUrl
    max_depth: Optional[int] = 5
    extract_depth: Optional[Literal["basic", "advanced"]] = "advanced"


class CrawlResponse(BaseModel):
    ok: bool
    url: str


class ChatRequest(BaseModel):
    query: str
    namespace: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[Dict[str, str]]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/crawl")
async def crawl_and_index(req: CrawlRequest) -> dict:
    start = time.perf_counter()
    try:
        await run_pipeline(
            str(req.url),
            max_depth=req.max_depth or 5,
            extract_depth=req.extract_depth or "advanced",
        )
        return CrawlResponse(ok=True, url=req.url)
    except KeyError as e:
        # Likely missing required env var
        raise HTTPException(status_code=500, detail=f"Missing configuration: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        elapsed = time.perf_counter() - start
    return {"status": "completed", "elapsed_seconds": round(elapsed, 3)}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

    try:
        result = await query_app.ainvoke(
            {
                "query": req.query,
                "namespace": req.namespace,
                "messages": [],
                "retrieved_docs": [],
                "context": "",
                "answer": "",
            },
            config={"configurable": {"thread_id": session_id}},
        )

        return ChatResponse(
            session_id=session_id,
            answer=result["answer"],
            sources=[
                {
                    "source": d.metadata.get("source", ""),
                    "chunk_id": d.metadata.get("chunk_id", ""),
                }
                for d in result["retrieved_docs"]
            ],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Proxy endpoint for LangGraph UI integration
@app.post("/ui/query")
async def ui_query_proxy(request: Request):
    """
    Adapter endpoint for LangGraph UI.

    Translates:
      LangGraph UI protocol
    into:
      existing /chat protocol
    """

    body = await request.json()

    # LangGraph UI request format
    input_state = body.get("input", {})
    configurable = body.get("configurable", {})

    query = input_state.get("query")
    thread_id = configurable.get("thread_id")

    if not query:
        raise HTTPException(status_code=400, detail="Missing query")

    # Call your existing chat logic directly
    result = await query_app.ainvoke(
        {
            "query": query,
            "messages": [],
            "retrieved_docs": [],
            "context": "",
            "answer": "",
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    # Return in LangGraph UI expected shape
    return {
        "output": {
            "query": query,
            "messages": result["messages"],
            "answer": result["answer"],
        }
    }


if __name__ == "__main__":
    # Allow running without uvicorn for quick local checks
    import uvicorn

    host = os.getenv("UVICORN_HOST", "127.0.0.1")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("server:app", host=host, port=port, reload=reload)
