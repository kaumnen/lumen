from ..parsing.pdf_parser import convert_pdf_to_markdown_document
from .chunk import chunk_markdown
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import Distance, VectorParams
from langchain_aws import BedrockEmbeddings
from langchain_core.documents import Document
import time
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

    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    return vector_store


def ingest_chunks_from_pdf(url, status=None):
    start_time = time.time()
    vector_store = _setup_qdrant_client()

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

    documents = []

    for i in range(len(text_chunks)):
        document = Document(
            page_content=text_chunks[i],
            metadata=metadatas[i],
        )
        documents.append(document)

    if status:
        status.write("Storing vectors...")
    vector_start = time.time()
    vector_store.add_documents(documents=documents)
    vector_time = time.time() - vector_start
    if status:
        status.write(f"Vectors stored successfully in {vector_time:.2f} seconds!")

    total_time = time.time() - start_time
    return total_time


def search_vectors(query_text, limit=10):
    vector_store = _setup_qdrant_client()
    results = vector_store.similarity_search(
        query=query_text,
        k=limit,
    )

    return results
