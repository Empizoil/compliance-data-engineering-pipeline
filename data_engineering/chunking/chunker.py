import tiktoken
import structlog
from dataclasses import dataclass
from data_engineering.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    token_count: int
    char_start: int
    char_end: int

class TextChunker:
    """ 
    Splits masked text into overlapping token-bounded chunks.

    Strategy: sentence-aware splitting with token-count enforcement.
    Overlap ensures that a compliance clause split across a chunk boundary
    is still fully represented in at least one chunk.

    Uses tiktoken for accurate token counting (cl100k_base encoding,
    compatible with most modern LLMs).
    """

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.chunk_size_tokens
        self.overlap = settings.chunk_overlap_tokens
        # cl100k_base is a good general-purpose encoding for token estimation
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def chunk(self, masked_text: str) -> list[TextChunk]:
        """
        Chunk masked text into overlapping windows.
        Returns list of TextChunk in document order.
        """
        if not masked_text.strip():
            return []

        tokens = self._encoder.encode(masked_text)
        total_tokens = len(tokens)

        chunks: list[TextChunk] = []
        chunk_index = 0
        start = 0

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self._encoder.decode(chunk_tokens)

            # Map back to character offsets in original text
            prefix_text = self._encoder.decode(tokens[:start])
            char_start = len(prefix_text)
            char_end = char_start + len(chunk_text)

            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    text=chunk_text,
                    token_count=len(chunk_tokens),
                    char_start=char_start,
                    char_end=char_end,
                )
            )

            chunk_index += 1

            # Advance by (chunk_size - overlap) to create the sliding window
            step = self.chunk_size - self.overlap
            start += step

            # Guard: if step is zero or negative, break to avoid infinite loop
            if step <= 0:
                break

        logger.info(
            "chunking_complete",
            total_tokens=total_tokens,
            chunk_count=len(chunks),
            chunk_size=self.chunk_size,
            overlap=self.overlap,
        )

        return chunks
