from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorDevice,
    AcceleratorOptions,
    TableFormerMode,
)
from docling.datamodel.base_models import InputFormat

from docling.datamodel.settings import settings


def convert_pdf_to_markdown_document(source_location):
    settings.debug.profile_pipeline_timings = True

    accelerator_options = AcceleratorOptions()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = accelerator_options
    pipeline_options.accelerator_options.device = AcceleratorDevice.AUTO
    pipeline_options.accelerator_options.cuda_use_flash_attention2 = True

    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = False
    pipeline_options.table_structure_options.mode = TableFormerMode.FAST

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )

    converter_result = converter.convert(source_location)

    doc_conversion_secs = converter_result.timings["pipeline_total"].times
    print(f"Conversion secs: {doc_conversion_secs}")

    markdown_document = converter_result.document

    return markdown_document
