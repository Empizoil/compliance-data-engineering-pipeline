from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractionResult:
    raw_text: str                # Full extracted text, concatenated
    page_count: Optional[int]    # Pages for PDF: sheets for XLSX; None for DOCX
    metadata: dict               # File specific metadata (e.g., author, created_at, title, etc.)
    warnings: list[str]


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """
        Extract plain text from file bytes.
        Must never raise on partial extraction - degrade gracefully and log warnings.
        """
        ...
        