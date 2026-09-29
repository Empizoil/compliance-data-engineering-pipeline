import asyncio
import structlog
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from data_engineering.config import get_settings

logger = structlog.get_logger(__name__)


class EmbeddingClient:
    """
    Wrapper around the Gemini embedding API.

    Key behaviours:
    - Batches requests to stay within free-tier rate limits
    - Retries on transient failures with exponential backoff
    - Validates that masked text is being embedded (callers' responsibility to pass masked text)
    - Never logs the text being embedded (privacy)
    """

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self._model = settings.embedding_model
        self._batch_size = settings.embedding_batch_size
        self._dimension = settings.embedding_dimension

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch. Retries on failure with exponential backoff."""
        result = genai.embed_content(
            model=self._model,
            content=texts,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=self._dimension,
        )
        embeddings = result["embedding"]
        # Validate dimension
        for emb in embeddings:
            if len(emb) != self._dimension:
                raise ValueError(
                    f"Unexpected embedding dimension: got {len(emb)}, expected {self._dimension}"
                )
        return embeddings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts in batches.
        Returns embeddings in the same order as input texts.

        IMPORTANT: Callers must pass masked text only.
        This method does not perform masking — that is the pipeline's responsibility.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            logger.info(
                "embedding_batch",
                batch_number=i // self._batch_size + 1,
                batch_size=len(batch),
            )
            try:
                batch_embeddings = self._embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error("embedding_batch_failed", batch_start=i, error=str(e))
                raise

        return all_embeddings

    def embed_single(self, text: str) -> list[float]:
        """Convenience wrapper for embedding a single text."""
        results = self.embed_texts([text])
        return results[0]