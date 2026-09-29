import structlog
from sqlalchemy import text
from data_engineering.db import get_db, set_ivfflat_probes
from data_engineering.config import get_settings
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class DisclosureCheckResult:
    disclosure_id: str
    disclosure_code: str
    title: str
    is_present: bool
    best_similarity: float      # Highest similarity score found across all chunks
    best_chunk_index: int | None  # Which chunk was closest to this disclosure


class DisclosureRetriever:
    """
    Checks whether each mandatory disclosure is present in a document.

    A disclosure is considered PRESENT if any document chunk has a cosine
    similarity >= threshold with the disclosure text in vector space.

    This catches reworded, reformatted, or paraphrased disclosures that
    keyword matching would miss.

    IMPORTANT: The threshold is a tuning parameter. Start at 0.78 and adjust
    based on empirical testing with your seeded documents.
    """

    def __init__(self):
        self._threshold = get_settings().disclosure_similarity_threshold

    def check_document(self, document_id: str) -> list[DisclosureCheckResult]:
        """
        Check all mandatory disclosures against a document's chunks.
        Returns one result per mandatory disclosure.
        """
        with get_db() as db:
            set_ivfflat_probes(db, probes=10)

            # Fetch all mandatory disclosures
            disclosures = db.execute(
                text("""
                    SELECT id, disclosure_code, title, body, embedding
                    FROM disclosure_texts
                    WHERE is_mandatory = TRUE
                    AND embedding IS NOT NULL
                """)
            ).fetchall()

            # Fetch all document chunks
            chunks = db.execute(
                text("""
                    SELECT chunk_index, embedding
                    FROM document_chunks
                    WHERE document_id = :doc_id
                    AND embedding IS NOT NULL
                    ORDER BY chunk_index
                """),
                {"doc_id": document_id},
            ).fetchall()

            if not chunks:
                logger.warning("no_chunks_for_disclosure_check", document_id=document_id)
                return []

            results: list[DisclosureCheckResult] = []

            for disclosure in disclosures:
                disc_embedding = disclosure.embedding
                best_sim = 0.0
                best_chunk_idx = None

                # Find the closest chunk to this disclosure
                for chunk in chunks:
                    # Cosine similarity via pgvector operator
                    sim_row = db.execute(
                        text("""
                            SELECT 1 - (embedding <=> :disc_emb::vector) AS similarity
                            FROM document_chunks
                            WHERE document_id = :doc_id
                            AND chunk_index = :chunk_idx
                        """),
                        {
                            "disc_emb": disc_embedding,
                            "doc_id": document_id,
                            "chunk_idx": chunk.chunk_index,
                        },
                    ).fetchone()

                    if sim_row and float(sim_row.similarity) > best_sim:
                        best_sim = float(sim_row.similarity)
                        best_chunk_idx = chunk.chunk_index

                is_present = best_sim >= self._threshold

                results.append(
                    DisclosureCheckResult(
                        disclosure_id=str(disclosure.id),
                        disclosure_code=disclosure.disclosure_code,
                        title=disclosure.title,
                        is_present=is_present,
                        best_similarity=best_sim,
                        best_chunk_index=best_chunk_idx,
                    )
                )

        missing = [r for r in results if not r.is_present]
        logger.info(
            "disclosure_check_complete",
            document_id=document_id,
            total_mandatory=len(results),
            missing_count=len(missing),
            threshold=self._threshold,
        )

        return results