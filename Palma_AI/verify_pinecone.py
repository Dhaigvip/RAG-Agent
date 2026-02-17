import os
import sys
from typing import Any

from dotenv import load_dotenv
from pinecone import Pinecone


def print_kv(label: str, value: Any) -> None:
    print(f"{label}: {value}")


def main() -> int:
    load_dotenv()

    api_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX")

    print_kv("API key set", bool(api_key))
    print_kv("Index name", index_name or "(not set)")

    if not api_key:
        print("ERROR: PINECONE_API_KEY is missing in environment/.env")
        return 1

    try:
        pc = Pinecone(api_key=api_key)
    except Exception as e:
        print("ERROR: Failed to create Pinecone client:", str(e))
        return 1

    # List indexes for a quick auth check
    try:
        indexes = pc.list_indexes()
        print_kv("Index count", len(indexes))
        if indexes:
            # Print a compact summary line for each index
            for ix in indexes:
                name = ix.get("name")
                dim = ix.get("dimension")
                ready = ix.get("status", {}).get("ready")
                region = (ix.get("spec", {}).get("serverless", {}) or {}).get("region")
                print(f"- {name} (dim={dim}, ready={ready}, region={region})")
    except Exception as e:
        print("ERROR: list_indexes failed:", str(e))
        return 1

    # If an index is specified, describe its stats
    if index_name:
        try:
            stats = pc.Index(index_name).describe_index_stats()
            print("Index stats:")
            print_kv("  dimension", stats.get("dimension"))
            print_kv("  metric", stats.get("metric"))
            print_kv("  total_vector_count", stats.get("total_vector_count"))
            print_kv("  namespaces", stats.get("namespaces"))
        except Exception as e:
            print(f"ERROR: describe_index_stats failed for '{index_name}':", str(e))
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
