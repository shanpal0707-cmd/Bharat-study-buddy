from pptx import Presentation


def extract_ppt_text(ppt_path):
    """
    Extract text from PowerPoint while preserving slide numbers.
    """

    presentation = Presentation(ppt_path)

    slides = []

    for slide_number, slide in enumerate(
        presentation.slides,
        start=1
    ):

        text_parts = []

        for shape in slide.shapes:

            if hasattr(shape, "text"):

                text = shape.text.strip()

                if text:
                    text_parts.append(text)

        slide_text = "\n".join(text_parts).strip()

        if slide_text:

            slides.append({
                "source": "PPT",
                "slide": slide_number,
                "text": slide_text
            })

    return slides