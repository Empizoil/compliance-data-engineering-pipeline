import structlog
from sqlalchemy import text
from data_engineering.db import get_db, set_ivfflat_probes
from data_engineering.embedding.embedder import EmbeddingClient
from data_engineering.config import get_settings

logger = structlog.get_logger(__name__)


class RuleRetriever:
    """
    For each chunk of a submitted document, retrieves the most semantically
    similar compliance rules from the rules corpus.

    The AI track uses these retrieved rules to anchor each flag to a specific rule,
    making flags traceable rather than generic.
    """

    def __init__(self):
        self._embedder = EmbeddingClient()
        self._top_k = get_settings().rule_retrieval_top_k

    def retrieve_for_document(self, document_id: str) -> list[dict]:
        """
        Run rule retrieval for all chunks of a document.
        Returns deduplicated list of relevant rules, ranked by average similarity.

        Returns:
            List of dicts: {rule_id, rule_code, title, body, rule_type, max_similarity}
        """
        with get_db() as db:
            set_ivfflat_probes(db, probes=10)

            # Fetch all chunks for the document
            chunk_rows = db.execute(
                text("""
                    SELECT id, masked_text, embedding
                    FROM document_chunks
                    WHERE document_id = :doc_id
                    AND embedding IS NOT NULL
                    ORDER BY chunk_index
                """),
                {"doc_id": document_id},
            ).fetchall()

            if not chunk_rows:
                logger.warning("no_chunks_found", document_id=document_id)
                return []

            # Collect rule hits across all chunks
            # rule_id -> best similarity score seen
            rule_scores: dict[str, float] = {}
            rule_data: dict[str, dict] = {}

            for chunk_row in chunk_rows:
                chunk_embedding = chunk_row.embedding

                results = db.execute(
                    text("""
                        SELECT
                            id,
                            rule_code,
                            title,
                            body,
                            rule_type,
                            1 - (embedding <=> :embedding::vector) AS similarity
                        FROM compliance_rules
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> :embedding::vector
                        LIMIT :top_k
                    """),
                    {"embedding": chunk_embedding, "top_k": self._top_k},
                ).fetchall()

                for row in results:
                    rule_id = str(row.id)
                    sim = float(row.similarity)
                    if rule_id not in rule_scores or rule_scores[rule_id] < sim:
                        rule_scores[rule_id] = sim
                        rule_data[rule_id] = {
                            "rule_id": rule_id,
                            "rule_code": row.rule_code,
                            "title": row.title,
                            "body": row.body,
                            "rule_type": row.rule_type,
                            "max_similarity": sim,
                        }

        # Sort by best similarity score and return top results
        ranked = sorted(rule_data.values(), key=lambda x: x["max_similarity"], reverse=True)
        top_rules = ranked[: self._top_k * 2]  # Return a generous set for the AI to work with

        logger.info(
            "rule_retrieval_complete",
            document_id=document_id,
            rules_retrieved=len(top_rules),
        )

        return top_rules