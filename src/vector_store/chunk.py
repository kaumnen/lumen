from docling.chunking import HybridChunker


def chunk_markdown(markdown_document):
    text_chunks, metadatas = [], []

    chunker = HybridChunker(tokenizer="sentence-transformers/all-MiniLM-L6-v2")
    chunk_iter = chunker.chunk(markdown_document)

    for chunk in chunk_iter:
        text_chunks.append(chunk.text)
        metadatas.append(chunk.meta.export_json_dict())

    return text_chunks, metadatas
