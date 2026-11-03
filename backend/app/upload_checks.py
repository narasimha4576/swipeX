import io

from fastapi import HTTPException
from pypdf import PdfReader

MAX_PAGES = 10
# A resume has no reason to contain scripts, launch actions or hidden attachments.
RISKY_MARKERS = (b"/JavaScript", b"/Launch", b"/EmbeddedFile")


def validate_pdf(content: bytes) -> None:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    if any(marker in content for marker in RISKY_MARKERS):
        raise HTTPException(
            status_code=400,
            detail="This PDF contains scripts or attachments. Please save a plain copy and upload that.",
        )
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Password-protected PDFs cannot be used. Please upload an unlocked copy.",
            )
        pages = len(reader.pages)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400, detail="This PDF is damaged or cannot be read. Please upload another copy."
        )
    if pages < 1:
        raise HTTPException(status_code=400, detail="This PDF has no pages")
    if pages > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"A resume can have at most {MAX_PAGES} pages")