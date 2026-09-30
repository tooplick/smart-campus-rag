"""Initialize Qdrant collection for campus RAG.

Usage:
    python scripts/init-qdrant.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

COLLECTION_NAME = "campus_rag_chunks_v1"
VECTOR_DIMENSION = 1024  # Default for BGE-M3, adjust based on your embedding model


async def main():
    client = AsyncQdrantClient(url="http://localhost:6333")

    collections = await client.get_collections()
    names = [c.name for c in collections.collections]

    if COLLECTION_NAME in names:
        print(f"Collection '{COLLECTION_NAME}' already exists")
    else:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        print(f"Created collection '{COLLECTION_NAME}' (dim={VECTOR_DIMENSION})")

    # Create payload indexes
    for field in ["knowledge_base_id", "document_id", "content_type"]:
        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=PayloadSchemaType.INTEGER if field != "content_type" else PayloadSchemaType.KEYWORD,
        )
        print(f"Created payload index on '{field}'")

    print("Qdrant initialization complete")


if __name__ == "__main__":
    asyncio.run(main())
