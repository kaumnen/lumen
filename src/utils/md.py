import re


def adjust_markdown_headings(markdown_doc, toc):
    current_markdown = markdown_doc
    processed_headings = set()

    for heading_info in toc:
        level, heading_text, page_num = heading_info

        if page_num < 1:
            continue

        heading_text = heading_text.strip()
        if not heading_text:
            continue

        if heading_text in processed_headings:
            continue

        processed_headings.add(heading_text)

        target_prefix = "#" * level + " "

        escaped_heading = re.escape(heading_text)

        pattern = re.compile(r"^#+\s+{}$".format(escaped_heading), re.MULTILINE)

        replacement = target_prefix + heading_text

        current_markdown = pattern.sub(replacement, current_markdown)

    return current_markdown
