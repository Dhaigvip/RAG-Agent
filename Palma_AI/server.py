import asyncio
import time
import os
import logging
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

# write to stdio in development.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    # handlers=[
    #     logging.FileHandler("app.log"),
    #     logging.StreamHandler(),
    # ],
)

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Palma Help Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    logger.info("Health check requested")
    return {"status": "ok"}


@app.post("/crawl")
async def crawl_and_index(req: CrawlRequest) -> dict:
    start = time.perf_counter()
    logger.info(
        "Crawl started",
        extra={
            "url": str(req.url),
            "max_depth": req.max_depth,
            "extract_depth": req.extract_depth,
        },
    )

    try:
        await run_pipeline(
            str(req.url),
            max_depth=req.max_depth or 5,
            extract_depth=req.extract_depth or "advanced",
        )

        logger.info("Crawl completed successfully", extra={"url": str(req.url)})
        return CrawlResponse(ok=True, url=req.url)

    except KeyError as e:
        logger.exception("Missing configuration during crawl")
        raise HTTPException(status_code=500, detail=f"Missing configuration: {e}")

    except Exception as e:
        logger.exception("Unhandled error during crawl")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        elapsed = time.perf_counter() - start
        logger.info(
            "Crawl finished",
            extra={
                "url": str(req.url),
                "elapsed_seconds": round(elapsed, 3),
            },
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Ensure required environment variables are present before proceeding
    required_env = ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX"]
    missing = [k for k in required_env if not os.getenv(k)]
    if missing:
        logger.error("Missing environment configuration", extra={"missing": missing})
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment configuration: {', '.join(missing)}",
        )
    session_id = req.session_id or str(uuid4())

    logger.info(
        "Chat request received",
        extra={
            "session_id": session_id,
            "namespace": req.namespace,
        },
    )

    try:
        start = time.perf_counter()

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

        elapsed = time.perf_counter() - start

        logger.info(
            "Chat completed",
            extra={
                "session_id": session_id,
                "elapsed_seconds": round(elapsed, 3),
                "sources_count": len(result.get("retrieved_docs", [])),
            },
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
        logger.exception(
            "Unhandled error during chat",
            extra={"session_id": session_id},
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ui/query")
async def ui_query_proxy(request: Request):
    logger.info("UI query proxy request received")

    body = await request.json()

    input_state = body.get("input", {})
    configurable = body.get("configurable", {})

    query = input_state.get("query")
    namespace = input_state.get("namespace")
    thread_id = configurable.get("thread_id")

    if not query:
        logger.warning("UI query missing query field")
        raise HTTPException(status_code=400, detail="Missing query")

    if not namespace:
        logger.warning("UI query missing namespace field")
        raise HTTPException(status_code=400, detail="Missing namespace")

    logger.info(
        "UI query forwarded to chat",
        extra={"thread_id": thread_id},
    )

    result = await query_app.ainvoke(
        {
            "query": query,
            "namespace": namespace,
            "messages": [],
            "retrieved_docs": [],
            "context": "",
            "answer": "",
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    logger.info(
        "UI query completed",
        extra={"thread_id": thread_id},
    )

    return {
        "output": {
            "query": query,
            "messages": result["messages"],
            "answer": result["answer"],
        }
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("UVICORN_HOST", "127.0.0.1")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"

    logger.info(
        "Starting server",
        extra={
            "host": host,
            "port": port,
            "reload": reload,
        },
    )

    uvicorn.run("server:app", host=host, port=port, reload=reload)
