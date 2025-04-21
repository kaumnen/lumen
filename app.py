import streamlit as st

st.set_page_config(page_title="lumen", page_icon="🟡", layout="wide")

chat = st.Page("ui/rag/chat.py", title="Chat", icon="💬")
search_vectors = st.Page("ui/rag/search.py", title="Search Vectors", icon="🔍")
pdf = st.Page("ui/rag/add_pdf.py", title="Add AWS Docs PDF", icon="👉")

pg = st.navigation(
    {
        "General": [chat],
        "Vectors": [pdf, search_vectors],
    }
)

pg.run()
