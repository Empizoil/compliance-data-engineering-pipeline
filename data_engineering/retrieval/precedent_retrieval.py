import structlog
from sqlalchemy import text
from data_engineering.db import get_db, set_ivfflat_probes
from data_engineering.config import get_settings
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class PrecedentResult:
    document_id: str
    decision: str           # approved | rejected | needs_revision
    officer_comment: str | None
    decided_at: str
    similarity: float


class PrecedentRetriever:
    """
    Finds the N most similar previously-reviewed documents for a new submission.

    Uses the new document's chunk embeddings aggregated via an average embedding
    to represent the full document as a single vector, then queries the precedent index.

    Precedents are indexed after each officer decision — see index_document().
    """

    def __init__(self):
        self._top_k = get_settings().precedent_top_k  # Fixed at 3 by spec

    def retrieve(self, document_id: str) -> list[PrecedentResult]:
        """
        Retrieve the top-K most similar precedents for a given document.
        The given document must already have chunks with embeddings.
        """
        with get_db() as db:
            set_ivfflat_probes(db, probes=10)

            # Compute the document's aggregate embedding by averaging chunk embeddings
            avg_embedding_row = db.execute(
                text("""
                    SELECT AVG(embedding) AS avg_embedding
                    FROM document_chunks
                    WHERE document_id = :doc_id
                    AND embedding IS NOT NULL
                """),
                {"doc_id": document_id},
            ).fetchone()

            if not avg_embedding_row or avg_embedding_row.avg_embedding is None:
                logger.warning("no_embedding_for_precedent_search", document_id=document_id)
                return []

            avg_embedding = avg_embedding_row.avg_embedding

            rows = db.execute(
                text("""
                    SELECT
                        p.document_id,
                        p.decision,
                        p.officer_comment,
                        p.decided_at,
                        1 - (p.embedding <=> :avg_emb::vector) AS similarity
                    FROM precedent_index p
                    WHERE p.document_id != :doc_id     -- exclude the document itself
                    AND p.embedding IS NOT NULL
                    ORDER BY p.embedding <=> :avg_emb::vector
                    LIMIT :top_k
                """),
                {
                    "avg_emb": avg_embedding,
                    "doc_id": document_id,
                    "top_k": self._top_k,
                },
            ).fetchall()

        results = [
            PrecedentResult(
                document_id=str(row.document_id),
                decision=row.decision,
                officer_comment=row.officer_comment,
                decided_at=str(row.decided_at),
                similarity=float(row.similarity),
            )
            for row in rows
        ]

        logger.info(
            "precedent_retrieval_complete",
            document_id=document_id,
            precedents_found=len(results),
        )

        return results

    def index_document(
        self,
        document_id: str,
        masked_summary: str,
        decision: str,
        officer_comment: str | None,
        decided_at: str,
        embedding: list[float],
    ) -> None:
        """
        Add a reviewed document to the precedent index.
        Called by the backend after an officer records a decision.

        masked_summary: truncated masked text (e.g. first 2000 chars of masked document).
        embedding: pre-computed embedding of the masked_summary.
        """
        with get_db() as db:
            db.execute(
                text("""
                    INSERT INTO precedent_index
                        (document_id, masked_summary, decision, officer_comment, decided_at, embedding, embedded_at)
                    VALUES
                        (:doc_id, :summary, :decision, :comment, :decided_at, :embedding::vector, NOW())
                    ON CONFLICT (document_id) DO UPDATE
                        SET decision = EXCLUDED.decision,
                            officer_comment = EXCLUDED.officer_comment,
                            decided_at = EXCLUDED.decided_at,
                            embedding = EXCLUDED.embedding,
                            embedded_at = NOW()
                """),
                {
                    "doc_id": document_id,
                    "summary": masked_summary[:3000],  # Cap stored summary length
                    "decision": decision,
                    "comment": officer_comment,
                    "decided_at": decided_at,
                    "embedding": embedding,
                },
            )

        logger.info("precedent_indexed", document_id=document_id, decision=decision)