import io
import structlog
import pdfplumber
from .base import BaseExtractor, ExtractionResult

logger = structlog.get_logger(__name__)

class PDFExtractor(BaseExtractor):  
    """
    Extract text from PDF files page by page.
    Uses pdfplumber for reliable text extraction from financial documents.
    Fails back to empty string per page on extraction failur (never raises).
    """

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:  
        pages_text: list[str] = []
        warnings: list[str] = []
        metadata: dict = {}

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                metadata = {
                    "page_count": len(pdf.pages),
                    "metadata": pdf.metadata or {},
                }

                for i, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text(x_tolerance=2, y_tolerance=2)
                        if text:
                            pages_text.append(f"[PAGE {i + 1}]\n{text.strip()}")
                        else:
                            warnings.append(f"Page {i + 1} has no extractable text (possibly scanned image).")
                    except Exception as e:
                            warnings.append(f"Page {i + 1} extraction error - {e}")
                            logger.warning("pdf_page_extraction_failed", page=i + 1, filename=filename, error=str(e))

        except Exception as e:
                logger.error("pdf_extraction_failed", filename=filename, error=str(e))
                raise ValueError(f"Could not open PDF '{filename}': {e}") from e

        raw_text = "\n\n".join(pages_text)

        if not raw_text.strip():
                warnings.append("Extracted text is empty. Document may be image-only.")

        logger.info(
                "pdf_extracted",
                filename=filename,
                pages=len(pages_text),
                char_count=len(raw_text),
                warnings=len(warnings),
        )

        return ExtractionResult(
                raw_text=raw_text,
                page_count=len(pdf.pages) if "page_count" not in metadata else metadata["page_count"],
                metadata=metadata,
                warnings=warnings,
            )