import asyncio
import os
import logging
from typing import TypedDict, List, Annotated

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

from langchain_core.documents import Document
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
)
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv

# from langchain_ollama import ChatOllama


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

load_dotenv()


class QueryState(TypedDict):
    query: str
    namespace: str
    messages: Annotated[List[BaseMessage], add_messages]
    retrieved_docs: List[Document]
    context: str
    answer: str


def build_context(docs: List[Document], max_chars: int = 4000) -> str:
    logger.info(
        "Building context",
        extra={"documents": len(docs), "max_chars": max_chars},
    )

    parts = []
    total = 0

    for doc in docs:
        text = (doc.page_content or "").strip()
        if not text:
            continue
        if total + len(text) > max_chars:
            break
        parts.append(text)
        total += len(text)

    logger.info(
        "Context built",
        extra={"total_chars": total},
    )

    return "\n\n---\n\n".join(parts)


async def retrieve(state: QueryState) -> QueryState:
    logger.info(
        "Retrieve node started",
        extra={
            "query": state["query"],
            "namespace": state["namespace"],
        },
    )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = PineconeVectorStore.from_existing_index(
        index_name=os.environ["PINECONE_INDEX"],
        embedding=embeddings,
        namespace=state["namespace"],
    )

    docs = await asyncio.to_thread(
        vector_store.similarity_search,
        state["query"],
        6,
    )

    logger.info(
        "Retrieve node completed",
        extra={"documents": len(docs)},
    )

    return {**state, "retrieved_docs": docs}


async def assemble_context(state: QueryState) -> QueryState:
    logger.info(
        "Assemble context node started",
        extra={"documents": len(state["retrieved_docs"])},
    )

    context = build_context(state["retrieved_docs"])

    logger.info(
        "Assemble context node completed",
        extra={"context_length": len(context)},
    )

    return {**state, "context": context}


async def generate(state: QueryState) -> QueryState:
    logger.info(
        "Generate node started",
        extra={
            "messages": len(state["messages"]),
            "context_length": len(state["context"]),
        },
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    # llm = ChatOllama(model="llama3.2:latest", temperature=0.2)

    system = SystemMessage(
        content=(
            "You are retrieval augmented assistent."
            "Answer using only provided context."
            "If the answer is not contained in the context, say"
            '"I do not know based on the provided sources."'
        )
    )

    human = HumanMessage(
        content=f"Question:\n{state['query']}\n\nContext:\n{state['context']}"
    )

    response = await llm.ainvoke([system, *state["messages"], human])

    logger.info(
        "Generate node completed",
        extra={"answer_length": len(response.content)},
    )

    return {
        **state,
        "messages": [human, response],
        "answer": response.content,
    }


checkpointer = MemorySaver()
graph = StateGraph(QueryState)

graph.add_node("retrieve", retrieve)
graph.add_node("assemble_context", assemble_context)
graph.add_node("generate", generate)

graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "assemble_context")
graph.add_edge("assemble_context", "generate")
graph.set_finish_point("generate")

query_app = graph.compile(checkpointer=checkpointer)