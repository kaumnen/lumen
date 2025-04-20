import streamlit as st

st.set_page_config(page_title="lumen", page_icon="🟡")

pdf = st.Page("rag/vectorize_pdf.py", title="Add PDF", icon="📄")

settings = st.Page("general/settings.py", title="Settings", icon="⚙️")

home = st.Page("general/home.py", title="Home", icon="🏠")

pg = st.navigation({"Home": [home], "Vectors": [pdf], "Settings": [settings]})

pg.run()
