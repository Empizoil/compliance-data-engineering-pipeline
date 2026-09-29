import io
import structlog
from docx import Document
from docx.oxml.ns import qn
from .base import BaseExtractor, ExtractionResult

logger = structlog.get_logger(__name__)

class DOCXExtractor(BaseExtractor):
    """
    Extract text from DOCX files, including tables.
    Tables are flattened row-by-row so compliance clauses in table cells are captured.
    """

    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        warnings: list[str] = []
        sections: list[str] = []

        try:
            doc = Document(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Could not open DOCX '{filename}': {e}") from e

        # Extract core properties for metadata
        core_props = doc.core_properties
        metadata = {
            "author": core_props.author,
            "created": str(core_props.created),
            "modified": str(core_props.modified),          
        }

        # Iterate document body in order (paragraphs and tables interleaved)
        for element in doc.element.body:
            tag = element.tag.split('}')[-1]  if '}' in element.tag else element.tag

            if tag == 'p':  # Paragraph
                text = "".join(run.text for run in element.findall(".//" + qn("w:t")))
                if text.strip():
                    sections.append(text.strip())

            elif tag == 'tbl':  # Table - flatten each row into a pipe-delimited line
                rows = element.findall(".//" + qn("w:tr"))
                for row in rows:
                    cells = row.findall(".//" + qn("w:tc"))
                    cell_texts = []
                    for cell in cells:
                        cell_text = " ".join(
                            t.text or "" for t in cell.findall(".//" + qn("w:t"))
                        ).strip()
                        cell_texts.append(cell_text)
                    row_text = " | ".join(cell_texts)
                    if row_text.strip():
                        sections.append(f"[TABLE ROW] {row_text}")

        raw_text = "\n".join(sections)

        if not raw_text.strip():
            warnings.append("Extracted text is empty")

        logger.info(
            "docx_extracted",
            filename=filename,
            section_count=len(sections),
            char_count=len(raw_text),
        )

        return ExtractionResult(
            raw_text=raw_text,
            page_count=None,
            metadata=metadata,
            warnings=warnings,
        ) 