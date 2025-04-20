from ..parsing.pdf_parser import convert_pdf_to_markdown_document
from .chunk import chunk_markdown
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import Distance, VectorParams
from langchain_aws import BedrockEmbeddings
from langchain_core.documents import Document

from dotenv import load_dotenv

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


markdown_document = convert_pdf_to_markdown_document()
text_chunks, metadatas = chunk_markdown(markdown_document)

documents = []

for i in range(len(text_chunks)):
    document = Document(
        page_content=text_chunks[i],
        metadata=metadatas[i],
    )
    documents.append(document)

vector_store.add_documents(documents=documents)

results = vector_store.similarity_search(
    query="Uploading and downloading multiple files using zipped folders",
    k=10,
)

for res in results:
    print(f"* {res.page_content} [{res.metadata}]")
