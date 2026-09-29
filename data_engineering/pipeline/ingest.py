"""
Document ingestion pipeline.
Orchestrates: extract → mask → store PII mapping → chunk → embed → store chunks.

Called by the backend immediately after a document upload is validated.
This is the hot path — keep it fast and idempotent.
"""

import structlog
from uuid import UUID
from sqlalchemy import text
from data_engineering.db import get_db
from data_engineering.extraction.router import extract_text
from data_engineering.masking.masker import PIIMasker
from data_engineering.chunking.chunker import TextChunker
from data_engineering.embedding.embedder import EmbeddingClient

logger = structlog.get_logger(__name__)

_masker = PIIMasker()
_chunker = TextChunker()
_embedder = EmbeddingClient()


def ingest_document(document_id: str, file_bytes: bytes, filename: str) -> dict:
    """
    Full ingestion pipeline for a newly uploaded document.

    Steps:
    1. Extract text from file
    2. Mask PII
    3. Persist PII mapping (server-side only)
    4. Chunk masked text
    5. Embed chunks
    6. Persist chunks + embeddings

    Returns a summary dict for logging/monitoring.
    Raises on unrecoverable errors (file corruption, embedding API failure).

    This function is IDEMPOTENT — safe to retry. On re-run, existing chunks
    are deleted and replaced (handles retry after partial failure).
    """
    logger.info("ingestion_started", document_id=document_id, filename=filename)

    # ── Step 1: Extract ──────────────────────────────────────────────────────
    extraction = extract_text(file_bytes, filename)
    if not extraction.raw_text.strip():
        raise ValueError(f"Document '{filename}' yielded no extractable text.")

    # ── Step 2: Mask ─────────────────────────────────────────────────────────
    masking_result = _masker.mask(extraction.raw_text)

    # ── Step 3: Persist PII mapping ──────────────────────────────────────────
    with get_db() as db:
        # Delete any existing mapping for idempotency
        db.execute(
            text("DELETE FROM pii_mappings WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )
        for placeholder, original_value in masking_result.mapping.items():
            # Determine entity type from placeholder format e.g. [CLIENT_1] -> NAME
            entity_type = _entity_type_from_placeholder(placeholder)
            db.execute(
                text("""
                    INSERT INTO pii_mappings (document_id, placeholder, original_value, entity_type)
                    VALUES (:doc_id, :placeholder, :original, :entity_type)
                    
                """),
                {
                    "doc_id": document_id,
                    "placeholder": placeholder,
                    "original": original_value,
                    "entity_type": entity_type,
                },
            )

    # ── Step 4: Chunk ─────────────────────────────────────────────────────────
    chunks = _chunker.chunk(masking_result.masked_text)
    if not chunks:
        raise ValueError(f"Document '{filename}' produced no chunks after masking.")

    # ── Step 5: Embed ─────────────────────────────────────────────────────────
    # IMPORTANT: We embed masked_text only. This is the privacy guarantee.
    chunk_texts = [c.text for c in chunks]
    embeddings = _embedder.embed_texts(chunk_texts)

    # ── Step 6: Persist chunks ────────────────────────────────────────────────
    with get_db() as db:
        # Delete existing chunks (idempotency)
        db.execute(
            text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )

        for chunk, embedding in zip(chunks, embeddings):
            db.execute(
                text("""
                    INSERT INTO document_chunks
                        (document_id, chunk_index, masked_text, char_start, char_end,
                         token_count, embedding, embedded_at)
                    VALUES
                        (:doc_id, :chunk_index, :masked_text, :char_start, :char_end,
                         :token_count, CAST(:embedding AS vector), NOW())
                """),
                {
                    "doc_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "masked_text": chunk.text,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "token_count": chunk.token_count,
                    "embedding": embedding,
                },
            )

    summary = {
        "document_id": document_id,
        "filename": filename,
        "char_count": len(extraction.raw_text),
        "entities_masked": sum(masking_result.entity_counts.values()),
        "chunk_count": len(chunks),
        "extraction_warnings": extraction.warnings,
    }

    logger.info("ingestion_complete", **summary)
    return summary


def _entity_type_from_placeholder(placeholder: str) -> str:
    """Map placeholder format to entity type label."""
    label_map = {
        "CLIENT": "NAME",
        "EMAIL": "EMAIL",
        "PHONE": "PHONE",
        "ADDRESS": "ADDRESS",
        "ACCOUNT": "ACCOUNT",
        "SSN": "SSN",
        "AMOUNT": "DOLLAR_AMOUNT",
    }
    for label, entity_type in label_map.items():
        if f"[{label}_" in placeholder:
            return entity_type
    return "UNKNOWN"
