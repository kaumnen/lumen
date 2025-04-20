from ..parsing.pdf_parser import convert_pdf_to_markdown_document
from .chunk import chunk_markdown
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from langchain_aws import BedrockEmbeddings
from langchain_core.documents import Document
import time
import asyncio
from typing import List
from dotenv import load_dotenv


def _setup_qdrant_client():
    load_dotenv()

    COLLECTION_NAME = "AWS_DOCS"

    qdrant_client = QdrantClient(host="localhost", port=6333)

    if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    return qdrant_client, COLLECTION_NAME


async def _async_embed_texts(texts: List[str]) -> List[List[float]]:
    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
    return await embeddings.aembed_documents(texts)


def ingest_chunks_from_pdf(url, status=None):
    start_time = time.time()

    if status:
        status.write("Parsing PDF...")
    parse_start = time.time()
    markdown_document = convert_pdf_to_markdown_document(url)
    parse_time = time.time() - parse_start
    if status:
        status.write(f"PDF Parsed successfully in {parse_time:.2f} seconds.")

    if status:
        status.write("Chunking text...")
    chunk_start = time.time()
    text_chunks, metadatas = chunk_markdown(markdown_document)
    chunk_time = time.time() - chunk_start
    if status:
        status.write(f"Text chunked successfully in {chunk_time:.2f} seconds.")

    if status:
        status.write("Generating embeddings asynchronously...")
    vector_start = time.time()

    embeddings = asyncio.run(_async_embed_texts(text_chunks))

    client, collection_name = _setup_qdrant_client()

    points = []
    for i in range(len(text_chunks)):
        points.append(
            models.PointStruct(
                id=i,
                payload={"page_content": text_chunks[i], **metadatas[i]},
                vector=embeddings[i],
            )
        )

    client.upsert(collection_name=collection_name, points=points)

    vector_time = time.time() - vector_start
    if status:
        status.write(
            f"Vectors generated and stored successfully in {vector_time:.2f} seconds!"
        )

    total_time = time.time() - start_time
    return total_time


def search_vectors(query_text, limit=10):
    client, collection_name = _setup_qdrant_client()
    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")

    query_embedding = embeddings.embed_query(query_text)

    search_result = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=limit,
        with_payload=True,
    )

    results = []
    for scored_point in search_result:
        payload = scored_point.payload
        page_content = payload.pop("page_content")

        doc = Document(
            page_content=page_content,
            metadata=payload,
        )
        results.append(doc)

    return results
