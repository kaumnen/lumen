import pymupdf


def remove_toc_and_document_history_from_pdf(input_pdf_path, output_pdf_path):
    doc = pymupdf.open(input_pdf_path)

    toc = get_pdf_toc(input_pdf_path)

    for i in toc:
        _, heading, page_num = i
        doc_page_num = len(doc)

        if "Document History".lower() in heading.lower():
            doc.delete_pages(from_page=page_num - 1, to_page=doc_page_num - 1)
            break

    for i in range(len(toc)):
        _, heading, page_num = toc[i]
        _, _, next_page_num = toc[i + 1]

        if "Table of Contents".lower() in heading.lower():
            doc.delete_pages(from_page=0, to_page=next_page_num - 2)
            break

    doc.save(output_pdf_path)
    doc.close()

    toc_after_cleanup = get_pdf_toc(output_pdf_path)
    return toc_after_cleanup


def get_pdf_toc(input_pdf_path):
    doc = pymupdf.open(input_pdf_path)
    toc = doc.get_toc(simple=True)
    doc.close()
    return toc
