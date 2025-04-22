import streamlit as st
import asyncio
from urllib.parse import urlparse
import tempfile
import os
import time
import requests

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from src.vector_store.qdrant_manager import ingest_chunks_from_pdf
from src.utils.pdf import remove_toc_and_document_history_from_pdf

st.title("Add AWS Docs PDF")
st.markdown(
    "This page allows you to add a PDF from AWS documentation. The PDF will be:\n- optimized\n- parsed\n- vectorized and stored in the vector database"
)
st.info(
    "With Fast mode - you can track the progress of the PDF processing in the console.",
    icon="ℹ️",
)

tab1, tab2 = st.tabs(["💾 Upload PDF", "🔗 PDF from URL"])

with tab1:
    with st.form(key="pdf_upload_form", clear_on_submit=True, border=False):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        mode = st.radio(
            "Processing Mode",
            ["Fast (New)", "Regular (Slower)"],
            help="Fast mode is recommended for about 7x faster processing based on preliminary testing. Accuracy is very similar to the regular mode.",
        )
        submit_button = st.form_submit_button("Process PDF")
        if uploaded_file is not None and submit_button:
            with st.status("Processing PDF...", expanded=True) as status:
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        input_path = tmp_file.name

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix="_optimized.pdf"
                    ) as tmp_output:
                        output_path = tmp_output.name

                    status.write("✅ PDF uploaded successfully.")
                    status.write("⚙️ Optimizing PDF...")
                    pdf_optimization_start = time.time()
                    remove_toc_and_document_history_from_pdf(input_path, output_path)
                    pdf_optimization_time = time.time() - pdf_optimization_start
                    status.write(
                        f"✅ PDF optimization completed in {pdf_optimization_time:.2f} seconds."
                    )

                    total_time = ingest_chunks_from_pdf(
                        output_path, status=status, mode=mode.lower()
                    )

                    os.unlink(input_path)
                    os.unlink(output_path)

                    status.update(
                        label=f"👍 PDF processed and vectorized successfully in {(total_time + pdf_optimization_time):.2f} seconds!",
                        state="complete",
                        expanded=False,
                    )
                except Exception as e:
                    status.update(
                        label=f"An error occurred: {str(e)}",
                        state="error",
                        expanded=True,
                    )

with tab2:
    with st.form(key="url_form", clear_on_submit=True, border=False):
        url_input = st.text_input(
            "Enter URL:", placeholder="https://docs.aws.amazon.com/..."
        )
        mode = st.radio(
            "Processing Mode",
            ["Fast", "Regular"],
            help="Fast mode is recommended as it is about 7x faster processing based on preliminary testing.",
        )
        st.markdown(
            "Please ensure the URL is a valid AWS documentation link. For example: https://docs.aws.amazon.com/pdfs/AWSEC2/latest/UserGuide/ec2-ug.pdf"
        )

        submitted = st.form_submit_button("Submit")

    if submitted:
        if url_input:
            parsed_url = urlparse(url_input)

            clean_url = url_input.split("#")[0]
            parsed_url = urlparse(clean_url)

            if (
                parsed_url.scheme == "https"
                and "docs.aws.amazon.com" in parsed_url.netloc
                and parsed_url.path.endswith(".pdf")
            ):
                with st.status("Processing PDF...", expanded=True) as status:
                    try:
                        status.write("⚙️ Downloading PDF...")
                        pdf_download_start = time.time()

                        response = requests.get(clean_url, stream=True)
                        pdf_download_time = time.time() - pdf_download_start
                        status.write(
                            f"✅ PDF download completed in {pdf_download_time:.2f} seconds."
                        )

                        if response.status_code != 200:
                            raise Exception(
                                f"Failed to download PDF. Status code: {response.status_code}"
                            )

                        content_type = response.headers.get("content-type", "").lower()
                        if "application/pdf" not in content_type:
                            raise Exception(
                                f"URL does not point to a PDF file. Content type: {content_type}"
                            )

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".pdf"
                        ) as tmp_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    tmp_file.write(chunk)
                            input_path = tmp_file.name

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix="_optimized.pdf"
                        ) as tmp_output:
                            output_path = tmp_output.name

                        status.write("⚙️ Optimizing PDF...")
                        pdf_optimization_start = time.time()
                        remove_toc_and_document_history_from_pdf(
                            input_path, output_path
                        )
                        pdf_optimization_time = time.time() - pdf_optimization_start
                        status.write(
                            f"✅ PDF optimization completed in {pdf_optimization_time:.2f} seconds."
                        )

                        total_time = ingest_chunks_from_pdf(
                            output_path, status=status, mode=mode.lower()
                        )

                        os.unlink(input_path)
                        os.unlink(output_path)

                        status.update(
                            label=f"👍 PDF processed and vectorized successfully in {(total_time + pdf_download_time + pdf_optimization_time):.2f} seconds!",
                            state="complete",
                            expanded=False,
                        )

                    except Exception as e:
                        status.update(
                            label=f"An error occurred: {str(e)}",
                            state="error",
                            expanded=True,
                        )
            else:
                st.warning("Please enter a valid URL")
        else:
            st.warning("Please enter a URL.")
