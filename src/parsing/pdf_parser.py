import pymupdf4llm
from loguru import logger
from ..utils.pdf import get_pdf_toc
from ..utils.md import adjust_markdown_headings


def convert_pdf_to_markdown_document_docling(source_location):
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        AcceleratorDevice,
        AcceleratorOptions,
        TableFormerMode,
    )
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.settings import settings

    settings.debug.profile_pipeline_timings = True

    accelerator_options = AcceleratorOptions()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = accelerator_options
    pipeline_options.accelerator_options.device = AcceleratorDevice.AUTO
    pipeline_options.accelerator_options.cuda_use_flash_attention2 = True

    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )

    converter_result = converter.convert(source_location)

    doc_conversion_secs = converter_result.timings["pipeline_total"].times
    logger.info(f"Conversion secs: {doc_conversion_secs}")

    markdown_document = converter_result.document.export_to_markdown()

    toc = get_pdf_toc(source_location)

    markdown_document_with_fixed_headings = adjust_markdown_headings(
        markdown_document, toc
    )

    return markdown_document_with_fixed_headings


def convert_pdf_to_markdown_document_pymupdf4llm(source_location):
    markdown_document = pymupdf4llm.to_markdown(
        source_location, ignore_images=True, ignore_graphics=True, show_progress=True
    )

    return markdown_document
