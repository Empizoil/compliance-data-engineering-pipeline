import structlog

from sqlalchemy import text

from data_engineering.db import get_db
from data_engineering.embedding.embedder import EmbeddingClient

logger = structlog.get_logger(__name__)


DISCLOSURES = [
    {
        "disclosure_code": "DISC-001",
        "title": "Investment Risk Disclosure",
        "body": "The document must disclose the risks associated with the recommended investment products and strategies.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-002",
        "title": "Fees and Charges Disclosure",
        "body": "The document must clearly disclose applicable fees, charges, commissions, and other costs.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-003",
        "title": "Client Objectives Disclosure",
        "body": "The document must state the client's investment objectives and financial goals.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-004",
        "title": "Suitability Disclosure",
        "body": "The document must provide information supporting the suitability of the recommended investment for the client.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-005",
        "title": "Conflicts of Interest Disclosure",
        "body": "The document must disclose relevant conflicts of interest that could affect the recommendation.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-006",
        "title": "Product Information Disclosure",
        "body": "The document must provide sufficient information about the financial products being recommended.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-007",
        "title": "Performance Information Disclosure",
        "body": "Where performance information is presented, the document must provide appropriate context and supporting information.",
        "is_mandatory": True,
    },
    {
        "disclosure_code": "DISC-008",
        "title": "Regulatory Disclosure",
        "body": "The document must include applicable regulatory and compliance disclosures required for the financial service or product.",
        "is_mandatory": True,
    },
]


def seed_disclosures() -> None:
    embedder = EmbeddingClient()

    texts = [
        f"{disclosure['title']}. {disclosure['body']}"
        for disclosure in DISCLOSURES
    ]

    logger.info(
        "generating_disclosure_embeddings",
        count=len(texts),
    )

    embeddings = embedder.embed_texts(texts)

    with get_db() as db:
        for disclosure, embedding in zip(DISCLOSURES, embeddings):
            db.execute(
                text("""
                    INSERT INTO disclosure_texts (
                        disclosure_code,
                        title,
                        body,
                        is_mandatory,
                        embedding,
                        embedded_at
                    )
                    VALUES (
                        :disclosure_code,
                        :title,
                        :body,
                        :is_mandatory,
                        CAST(:embedding AS vector),
                        NOW()
                    )
                    ON CONFLICT (disclosure_code) DO UPDATE
                    SET
                        title = EXCLUDED.title,
                        body = EXCLUDED.body,
                        is_mandatory = EXCLUDED.is_mandatory,
                        embedding = EXCLUDED.embedding,
                        embedded_at = NOW()
                """),
                {
                    "disclosure_code": disclosure["disclosure_code"],
                    "title": disclosure["title"],
                    "body": disclosure["body"],
                    "is_mandatory": disclosure["is_mandatory"],
                    "embedding": str(embedding),
                },
            )

    logger.info(
        "disclosure_seeding_complete",
        count=len(DISCLOSURES),
    )


if __name__ == "__main__":
    seed_disclosures()