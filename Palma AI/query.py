# query_graph.py
import asyncio
import os
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

# Load environment variables from .env if present
load_dotenv()


class QueryState(TypedDict):
    query: str
    namespace: str
    messages: Annotated[List[BaseMessage], add_messages]
    retrieved_docs: List[Document]
    context: str
    answer: str


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def build_context(docs: List[Document], max_chars: int = 4000) -> str:
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

    return "\n\n---\n\n".join(parts)


async def retrieve(state: QueryState) -> QueryState:
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

    return {**state, "retrieved_docs": docs}


async def assemble_context(state: QueryState) -> QueryState:
    context = build_context(state["retrieved_docs"])
    return {**state, "context": context}


async def generate(state: QueryState) -> QueryState:
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
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
