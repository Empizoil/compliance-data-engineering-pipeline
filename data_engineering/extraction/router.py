import structlog
from .base import BaseExtractor, ExtractionResult
from .pdf_extractor import PDFExtractor
from .docx_extractor import DOCXExtractor
from .xlsx_extractor import XLSXExtractor


logger = structlog.get_logger(__name__)

_EXTRACTORS: dict[str, BaseExtractor] = {
    ".pdf": PDFExtractor(),
    ".docx": DOCXExtractor(),
    ".xlsx": XLSXExtractor(),
}

def extract_text(file_bytes: bytes, filename: str) -> ExtractionResult:
    """
    Route to the correct extractor based on file extension.
    Raises ValueError for unsupported file types
    """
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extractor = _EXTRACTORS.get(suffix)
    if not extractor:
        raise ValueError(
            f"Unsupported file type '{suffix}. Supported: {list(_EXTRACTORS.keys())}"
        )
    logger.info("extraction_started", filename=filename, file_type=suffix)
    result = extractor.extract(file_bytes, filename)
    logger.info(
        "extraction_complete",
        filename=filename,
        char_count=len(result.raw_text),
        warnings=result.warnings,
    )
    return result