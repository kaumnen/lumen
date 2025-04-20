import streamlit as st
import pandas as pd
from src.vector_store.qdrant_manager import search_vectors

st.title("Search Vectors")
st.markdown(
    "This page allows you to search vectors in the database. You can use the search bar below to find relevant information."
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
                    "File Name": [
                        vector.metadata["origin"]["filename"]
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
                    "File Name": st.column_config.TextColumn(
                        "File Name",
                        width="small",
                    ),
                },
            )
        else:
            st.warning("No vectors found for the given search term.")
    else:
        st.warning("Please enter a search term.")
