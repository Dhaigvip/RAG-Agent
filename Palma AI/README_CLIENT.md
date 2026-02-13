1. Crawl request
http://0.0.0.0:8000/crawl
{
    "url": "https://www.modularmanagement.com/",
    "max_depth": 5,
    "extract_depth": "advanced"
}

2. Query
http://0.0.0.0:8000/chat
{
    "query": "What services modular management provides?",
    "namespace": "https://www.modularmanagement.com/"
}

3. The Chat Response returns session_id. Include session_id in next request for continuation of conversation.
http://0.0.0.0:8000/chat
{
    "query": "What services modular management provides?",
    "namespace": "https://www.modularmanagement.com/"
    "session_id": "ID"
}

** A Pinecone Index is the core database structure that stores collections of high-dimensional vectors (numerical representations of data like text or images) for similarity search, while a Namespace is a logical partition within an index, allowing you to organize and isolate different datasets (e.g., for different users or environments) without creating separate indexes, simplifying data management and enabling multi-tenancy
