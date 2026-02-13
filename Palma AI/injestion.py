import asyncio
import os
import hashlib
import httpx
import logging
from typing import TypedDict, List, Dict, NotRequired

# cspell ignore tavily ainvoke

from langgraph.graph import StateGraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_tavily import TavilyCrawl as SearchCrawler

try:
    from pinecone import Pinecone as PineconeClient
except Exception:
    PineconeClient = None
    import pinecone as pinecone_v7

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

load_dotenv()


async def chunk_id(doc: Document, index: int) -> str:
    return f"{doc.metadata['source']}::chunk-{index}"


async def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def build_metadata(doc: Document, idx: int) -> Dict:
    return {
        **doc.metadata,
        "chunk_id": await chunk_id(doc, idx),
        "checksum": await checksum(doc.page_content),
    }


async def compute_delta(
    previous: Dict[str, Dict],
    current_chunks: List[Document],
) -> Dict[str, List[Document]]:

    logger.info(
        "Computing delta",
        extra={
            "previous_count": len(previous),
            "current_count": len(current_chunks),
        },
    )

    current_map = {}
    for idx, doc in enumerate(current_chunks):
        chunk = doc.copy()
        chunk.metadata.update(await build_metadata(chunk, idx))
        current_map[chunk.metadata["chunk_id"]] = chunk

    prev_ids = set(previous.keys())
    curr_ids = set(current_map.keys())

    new_ids = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids
    candidate_updates = curr_ids & prev_ids

    changed_ids = [
        cid
        for cid in candidate_updates
        if current_map[cid].metadata["checksum"] != previous[cid]["checksum"]
    ]

    logger.info(
        "Delta computed",
        extra={
            "new": len(new_ids),
            "changed": len(changed_ids),
            "removed": len(removed_ids),
        },
    )

    return {
        "new": [current_map[cid] for cid in new_ids],
        "changed": [current_map[cid] for cid in changed_ids],
        "removed": list(removed_ids),
    }


async def fetch_previous_signatures(pinecone_index, namespace: str) -> Dict[str, Dict]:
    logger.info("Fetching previous signatures", extra={"namespace": namespace})

    results = await asyncio.to_thread(
        lambda: pinecone_index.query(
            vector=[0.0],
            top_k=1,
            include_values=False,
            include_metadata=True,
            filter={"namespace": {"$eq": namespace}},
        )
    )

    signatures = {}
    for match in results.get("matches", []):
        meta = match["metadata"]
        signatures[meta["chunk_id"]] = {
            "checksum": meta["checksum"],
            "vector_id": match["id"],
        }

    logger.info(
        "Previous signatures fetched",
        extra={"count": len(signatures)},
    )

    return signatures


async def crawl_with_search_api(
    url: str,
    *,
    max_depth: int = 5,
    extract_depth: str = "advanced",
    headers: Dict[str, str] | None = None,
) -> List[Document]:

    logger.info(
        "Crawl started",
        extra={
            "url": url,
            "max_depth": max_depth,
            "extract_depth": extract_depth,
        },
    )

    crawl_tool = SearchCrawler()
    response = await asyncio.to_thread(
        crawl_tool.invoke,
        {
            "url": url,
            "max_depth": max_depth,
            "extract_depth": extract_depth,
        },
    )

    items = []
    if isinstance(response, dict):
        items = (
            response.get("results")
            or response.get("data")
            or response.get("documents")
            or []
        )
    elif isinstance(response, list):
        items = response
    elif isinstance(response, str):
        items = [{"raw_content": response, "url": url}]

    documents: List[Document] = []
    for item in items:
        if isinstance(item, str):
            content = item
            src = url
        elif isinstance(item, dict):
            content = (
                item.get("raw_content")
                or item.get("content")
                or item.get("text")
                or ""
            )
            src = item.get("url", url)
        else:
            continue

        if not content:
            continue

        documents.append(
            Document(
                page_content=content,
                metadata={"source": src},
            )
        )

    logger.info(
        "Crawl completed",
        extra={"documents": len(documents)},
    )

    return documents


async def batched(iterable, size=50):
    batches = []
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches


async def apply_delta(
    vector_store: PineconeVectorStore,
    delta: Dict,
    namespace: str,
    batch_size: int = 50,
):
    logger.info(
        "Applying delta",
        extra={
            "namespace": namespace,
            "new": len(delta["new"]),
            "changed": len(delta["changed"]),
            "removed": len(delta["removed"]),
        },
    )

    new_batches = await batched(delta["new"], batch_size)
    for docs in new_batches:
        await asyncio.to_thread(
            lambda docs=docs: vector_store.add_documents(docs, namespace=namespace)
        )

    changed_batches = await batched(delta["changed"], batch_size)
    for docs in changed_batches:
        await asyncio.to_thread(
            lambda docs=docs: vector_store.upsert_documents(docs, namespace=namespace)
        )

    removed_batches = await batched(delta["removed"], batch_size)
    for ids in removed_batches:
        await asyncio.to_thread(
            lambda ids=ids: vector_store.delete(ids=ids, namespace=namespace)
        )

    logger.info("Delta applied", extra={"namespace": namespace})


class CrawlState(TypedDict):
    url: str
    raw_docs: List[Document]
    chunks: List[Document]
    delta: Dict[str, List[Document] | List[str]]
    max_depth: NotRequired[int]
    extract_depth: NotRequired[str]


graph = StateGraph(CrawlState)


async def crawl(state: CrawlState) -> CrawlState:
    logger.info("Graph crawl node entered", extra={"url": state["url"]})

    docs = await crawl_with_search_api(
        state["url"],
        max_depth=state.get("max_depth", 5),
        extract_depth=state.get("extract_depth", "advanced"),
    )
    return {**state, "raw_docs": docs}


async def split(state: CrawlState) -> CrawlState:
    logger.info(
        "Splitting documents",
        extra={"raw_docs": len(state["raw_docs"])},
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = await asyncio.to_thread(splitter.split_documents, state["raw_docs"])

    for idx, chunk in enumerate(chunks):
        chunk.metadata.update(await build_metadata(chunk, idx))

    logger.info(
        "Split completed",
        extra={"chunks": len(chunks)},
    )

    return {**state, "chunks": chunks}


async def diff(state: CrawlState) -> CrawlState:
    namespace = state["url"]
    logger.info("Diff node started", extra={"namespace": namespace})

    if PineconeClient is not None:
        pinecone_client = PineconeClient(api_key=os.environ["PINECONE_API_KEY"])
        index = pinecone_client.Index(os.environ["PINECONE_INDEX"])
    else:
        pinecone_v7.init(api_key=os.environ["PINECONE_API_KEY"])
        index = pinecone_v7.Index(os.environ["PINECONE_INDEX"])

    previous = await fetch_previous_signatures(index, namespace)
    delta = await compute_delta(previous, state["chunks"])

    return {**state, "delta": delta}


async def persist(state: CrawlState) -> CrawlState:
    logger.info("Persist node started", extra={"namespace": state["url"]})

    vector_store = PineconeVectorStore.from_existing_index(
        index_name=os.environ["PINECONE_INDEX"],
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        namespace=state["url"],
    )

    await apply_delta(vector_store, state["delta"], namespace=state["url"])

    logger.info("Persist completed", extra={"namespace": state["url"]})

    return state


graph.add_node("crawl", crawl)
graph.add_node("split", split)
graph.add_node("diff", diff)
graph.add_node("persist", persist)
graph.set_entry_point("crawl")
graph.add_edge("crawl", "split")
graph.add_edge("split", "diff")
graph.add_edge("diff", "persist")
graph.set_finish_point("persist")

app = graph.compile()


async def run_pipeline(
    url: str,
    *,
    max_depth: int = 5,
    extract_depth: str = "advanced",
    headers: Dict[str, str] | None = None,
):
    logger.info(
        "Pipeline started",
        extra={
            "url": url,
            "max_depth": max_depth,
            "extract_depth": extract_depth,
        },
    )

    await app.ainvoke(
            {"url": url, "max_depth": max_depth, "extract_depth": extract_depth}
        )
    
    logger.info("Pipeline completed", extra={"url": url})

