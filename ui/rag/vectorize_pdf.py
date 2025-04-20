import streamlit as st
from urllib.parse import urlparse
from src.vector_store.qdrant_manager import ingest_chunks_from_pdf

st.title("Add AWS Docs PDF")
st.markdown(
    "This page allows you to add a PDF from AWS documentation. The PDF will be:\n- parsed\n- vectorized and\n- stored in the vector database"
)

with st.form(key="url_form"):
    url_input = st.text_input("Enter URL:")

    submitted = st.form_submit_button("Submit")

if submitted:
    if url_input:
        parsed_url = urlparse(url_input)
        if parsed_url.scheme == "https" and "docs.aws.amazon.com" in parsed_url.netloc:
            st.success(f"URL Valid: {url_input}")
            with st.spinner("Processing..."):
                ingest_chunks_from_pdf(url_input)
            st.success("PDF processed and vectorized successfully!")
        else:
            st.error(
                "**Invalid URL**\n\nThe URL must:\n- Use `HTTPS`\n- Be on the `docs.aws.amazon.com` domain",
                icon="🚫",
            )
    else:
        st.warning("Please enter a URL.")
