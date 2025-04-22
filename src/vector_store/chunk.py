from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from src.utils.pdf import get_pdf_title


def chunk_markdown(markdown_document, pdf_path):
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )

    md_header_splits = markdown_splitter.split_text(markdown_document)

    chunk_size = 10000
    chunk_overlap = 500
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    splits = text_splitter.split_documents(md_header_splits)

    min_chunk_length = 20
    filtered_splits = [
        doc for doc in splits if len(doc.page_content.strip()) >= min_chunk_length
    ]

    text_chunks = [doc.page_content for doc in filtered_splits]
    metadatas = [doc.metadata for doc in filtered_splits]

    title = get_pdf_title(pdf_path)
    for metadata in metadatas:
        metadata["Document title"] = title

    return text_chunks, metadatas
