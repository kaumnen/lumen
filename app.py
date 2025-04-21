import streamlit as st

st.set_page_config(page_title="lumen", page_icon="🟡", layout="wide")

home = st.Page("ui/general/home.py", title="Home", icon="🏠")

chat = st.Page("ui/rag/chat.py", title="Chat", icon="💬")
search_vectors = st.Page("ui/rag/search.py", title="Search Vectors", icon="🔍")
pdf = st.Page("ui/rag/add_pdf.py", title="Add AWS Docs PDF", icon="👉")
settings = st.Page("ui/general/settings.py", title="Settings", icon="⚙️")

pg = st.navigation(
    {
        "Home": [home],
        "Vectors": [pdf, search_vectors],
        "Chat": [chat],
        "Settings": [settings],
    }
)

pg.run()
