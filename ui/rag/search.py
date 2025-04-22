import streamlit as st
import pandas as pd
import re
from src.vector_store.qdrant_manager import search_vectors
from src.utils.qdrant import get_collection_metadata


st.title("Search Vectors")

with st.sidebar:
    st.markdown(
        """
    This page allows you to **search vectors** stored in the vector database. 
    
    You can use the search bar below and adjust the number of results to find relevant information.
    
"""
    )

    st.markdown("---")

    st.header("VectorDB Info")
    vector_count, collection_status, optimizer_status = get_collection_metadata()

    status_map = {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "grey": "🟠",
        "ok": "🟢",
    }
    collection_status_display = status_map.get(collection_status, "❓ Unknown status")
    optimizer_status_display = status_map.get(optimizer_status, "❓ Unknown status")

    info_data = {
        "Metric": ["Collection Status", "Optimizer Status", "Vector Count"],
        "Value": [
            collection_status_display,
            optimizer_status_display,
            str(vector_count),
        ],
    }
    info_df = pd.DataFrame(info_data)

    st.dataframe(
        info_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn(
                "Metric",
                width="medium",
            ),
            "Value": st.column_config.TextColumn(
                "Value",
                width="medium",
            ),
        },
    )

with st.form(key="search_text_form"):
    search_text = st.text_input("Enter content:")
    search_limit = st.number_input(
        "Number of results to return:", min_value=1, max_value=100, value=5
    )

    submitted = st.form_submit_button("Submit")

if submitted:
    if search_text:
        with st.spinner("Processing..."):
            found_vectors = search_vectors(search_text, limit=search_limit)
        st.toast("✅ Search completed successfully!")
        if found_vectors:
            st.write("## Vector search results:")
            st.info("💡 Double-click any cell to see the full content", icon="ℹ️")

            df = pd.DataFrame(
                {
                    "Result #": range(1, len(found_vectors) + 1),
                    "Content": [vector.page_content for vector in found_vectors],
                    "Document title": [
                        vector.metadata.get("Document title", "")
                        for vector in found_vectors
                    ],
                    "Headings": [
                        " -> ".join(
                            [
                                str(vector.metadata.get(key)).strip()
                                for key in sorted(
                                    [
                                        k
                                        for k in vector.metadata
                                        if re.match(r"Header \d+", k)
                                    ],
                                    key=lambda x: int(x.split(" ")[1]),
                                )
                                if vector.metadata.get(key)
                            ]
                        )
                        for vector in found_vectors
                    ],
                }
            )
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Result #": st.column_config.NumberColumn(
                        "Result #",
                        width="small",
                    ),
                    "Content": st.column_config.TextColumn(
                        "Content",
                        width="large",
                        help="Double-click to view full content",
                    ),
                    "Document title": st.column_config.TextColumn(
                        "Document title",
                        width="small",
                    ),
                    "Headings": st.column_config.TextColumn(
                        "Headings",
                        width="large",
                    ),
                },
            )
        else:
            st.warning("No vectors found for the given search term.")
    else:
        st.warning("Please enter a search term.")
