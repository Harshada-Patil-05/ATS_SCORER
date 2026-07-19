import logging

try:
    from weasyprint import HTML, CSS

    WEASYPRINT_INSTALLED = True

except Exception as e:
    WEASYPRINT_INSTALLED = False
    WEASYPRINT_ERROR = str(e)

logger = logging.getLogger("ats_resume_scorer")


def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:

    if not WEASYPRINT_INSTALLED:
        raise ImportError(
            f"WeasyPrint could not start.\nReason: {WEASYPRINT_ERROR}"
        )

    documents = []

    for html_str in html_docs.values():
        document = HTML(string=html_str).render()
        documents.append(document)

    if not documents:
        raise ValueError("No HTML documents were provided.")

    first_doc = documents[0]

    for other_doc in documents[1:]:
        first_doc.pages.extend(other_doc.pages)

    return first_doc.write_pdf()