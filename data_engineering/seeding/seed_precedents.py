import structlog
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from data_engineering.db import get_db
from data_engineering.embedding.embedder import EmbeddingClient

logger = structlog.get_logger(__name__)

SAMPLE_COUNT = 100

DECISIONS = [
    "approved",
    "rejected",
    "needs_revision",
]

SUMMARIES = [
    "Investment advisory document covering portfolio allocation, investment objectives, risk factors, and required disclosures.",
    "Financial planning document covering client objectives, recommended products, fees, risks, and regulatory disclosures.",
    "Advisory report covering investment performance, portfolio recommendations, material risks, and client suitability information.",
    "Client-facing financial document covering recommended investments, associated risks, charges, and mandatory regulatory disclosures.",
]


def generate_sample_precedent(index: int) -> dict:
    return {
        "document_id": str(uuid4()),
        "masked_summary": SUMMARIES[index % len(SUMMARIES)],
        "decision": DECISIONS[index % len(DECISIONS)],
        "officer_comment": "Synthetic seed precedent used for retrieval testing.",
        "decided_at": (
            datetime.utcnow() - timedelta(days=index)
        ).isoformat(),
    }


def seed_precedents() -> None:
    precedents = [
        generate_sample_precedent(i)
        for i in range(SAMPLE_COUNT)
    ]

    summaries = [
        precedent["masked_summary"]
        for precedent in precedents
    ]

    logger.info(
        "generating_precedent_embeddings",
        count=len(summaries),
    )

    embedder = EmbeddingClient()
    embeddings = embedder.embed_texts(summaries)

    with get_db() as db:

        # Create the parent document records first.
        for precedent in precedents:
            db.execute(
                text("""
                    INSERT INTO documents (
                        id,
                        filename,
                        content
                    )
                    VALUES (
                        :document_id,
                        :filename,
                        :content
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "document_id": precedent["document_id"],
                    "filename": (
                        f"synthetic_precedent_"
                        f"{precedent['document_id']}.txt"
                    ),
                    "content": precedent["masked_summary"],
                },
            )

        # Create the corresponding precedent records.
        for precedent, embedding in zip(precedents, embeddings):
            db.execute(
                text("""
                    INSERT INTO precedent_index (
                        document_id,
                        masked_summary,
                        decision,
                        officer_comment,
                        decided_at,
                        embedding,
                        embedded_at
                    )
                    VALUES (
                        :document_id,
                        :masked_summary,
                        :decision,
                        :officer_comment,
                        :decided_at,
                        CAST(:embedding AS vector),
                        NOW()
                    )
                    ON CONFLICT (document_id) DO NOTHING
                """),
                {
                    "document_id": precedent["document_id"],
                    "masked_summary": precedent["masked_summary"],
                    "decision": precedent["decision"],
                    "officer_comment": precedent["officer_comment"],
                    "decided_at": precedent["decided_at"],
                    "embedding": str(embedding),
                },
            )

    logger.info(
        "precedent_seeding_complete",
        count=len(precedents),
    )


if __name__ == "__main__":
    seed_precedents()