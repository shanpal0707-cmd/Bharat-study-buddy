import fitz


def extract_pdf_text(pdf_path):
    """
    Extract text from PDF while preserving page numbers.
    """

    document = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(document, start=1):

        text = page.get_text("text").strip()

        if text:
            pages.append({
                "source": "PDF",
                "page": page_number,
                "text": text
            })

    document.close()

    return pages