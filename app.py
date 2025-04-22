import streamlit as st

st.set_page_config(page_title="lumen", page_icon="🟡", layout="wide")
st.logo(
    '<svg viewBox="0 0 130 36" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="iconify iconify--twemoji"><g stroke-width="0"/><g stroke-linecap="round" stroke-linejoin="round"/><circle fill="#FDCB58" cx="18" cy="18" r="18"/><text x="50" y="20" font-size="30" font-family="Arial, sans-serif" dominant-baseline="middle">lumen</text></svg>'
)

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
