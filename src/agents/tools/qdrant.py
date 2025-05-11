from langchain_core.tools import tool
from ...vector_store.qdrant_manager import (
    search_vectors,
)
from langchain_core.documents import Document
from typing import List
import re
from loguru import logger

MAX_CHARS_PER_RESULT = 10000
MAX_TOTAL_CHARS = 50000


@tool
def search_local_aws_docs(query: str, num_results: int = 5) -> str:
    """
    Searches the locally stored and vectorized AWS documentation PDFs for relevant information based on the user's query.
    Use this tool when the user asks questions about AWS services, features, or procedures that might be found in the ingested PDF documents.
    You can provide the user's specific question as the 'query' either raw or optimized if you think it will improve the search results.
    You can optionally specify 'num_results' (default is 5) for the number of search results to retrieve.
    """
    logger.debug("--- Executing Qdrant Search Tool ---")
    logger.debug(f"Query: {query}, Limit: {num_results}")
    try:
        found_docs: List[Document] = search_vectors(query_text=query, limit=num_results)

        if not found_docs:
            return "No relevant documents found in the local AWS documentation store."

        results_str = "Found the following relevant snippets from local AWS docs:\n\n"
        total_chars = len(results_str)

        for i, doc in enumerate(found_docs):
            page_content = doc.page_content.strip()
            headers = " -> ".join(
                [
                    str(doc.metadata.get(key)).strip()
                    for key in sorted(
                        [k for k in doc.metadata if re.match(r"Header \d+", k)],
                        key=lambda x: int(x.split(" ")[1]),
                    )
                    if doc.metadata.get(key)
                ]
            )

            metadata_info = f"(Source: {doc.metadata.get('Document title', 'N/A')}, Heading(s): {headers})"

            # Truncate individual result if too long
            truncated_content = page_content[:MAX_CHARS_PER_RESULT]
            if len(page_content) > MAX_CHARS_PER_RESULT:
                truncated_content += "..."

            entry = f"Result {i + 1}:\n{truncated_content}\n{metadata_info}\n\n"

            if total_chars + len(entry) > MAX_TOTAL_CHARS:
                results_str += (
                    "--- More results available but truncated due to length limit ---"
                )
                break

            results_str += entry
            total_chars += len(entry)

        logger.debug(f"--- Qdrant Search Tool Results ---\n{results_str}")
        return results_str.strip()

    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return (
            f"An error occurred while searching the local AWS documentation: {str(e)}"
        )
