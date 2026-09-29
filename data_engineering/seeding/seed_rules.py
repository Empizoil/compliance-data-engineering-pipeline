"""
Seed compliance rules into the database.

Rules are loaded from data/rules.json — a JSON array of rule objects.
Generate the JSON content with an LLM (Gemini, ChatGPT) using the prompt below.

GENERATION PROMPT (run once, save output as data/rules.json):
---
Generate 40 plausible financial compliance rules for a US-based wealth management firm.
Cover: required disclosures, prohibited language, performance claim standards, and required fields.
Format as a JSON array. Each rule object must have:
  - rule_code: string (e.g. "PERF-001")
  - rule_type: one of DISCLOSURE | PROHIBITED_CLAIM | PERFORMANCE_STANDARD | REQUIRED_FIELD
  - title: string (one line)
  - body: string (2–4 sentences describing the rule)
Use plausible regulatory language modelled on SEC and FINRA advertising standards.
Use no real client names or data.
---
"""

import json
import structlog
from pathlib import Path
from data_engineering.db import get_db
from data_engineering.embedding.embedder import EmbeddingClient
from sqlalchemy import text

logger = structlog.get_logger(__name__)

RULES_FILE = Path(__file__).parent / "data" / "rules.json"


def seed_rules(force: bool = False) -> int:
    """
    Load rules from JSON and insert with embeddings into compliance_rules table.

    Args:
        force: if True, truncates existing rules before seeding.
    Returns:
        Number of rules inserted.
    """
    if not RULES_FILE.exists():
        raise FileNotFoundError(f"Rules file not found: {RULES_FILE}")

    rules = json.loads(RULES_FILE.read_text())
    embedder = EmbeddingClient()

    with get_db() as db:
        if force:
            db.execute(text("TRUNCATE TABLE compliance_rules CASCADE"))
            logger.warning("rules_table_truncated")

        # Check if already seeded
        count_row = db.execute(text("SELECT COUNT(*) FROM compliance_rules")).fetchone()
        if count_row and count_row[0] > 0 and not force:
            logger.info("rules_already_seeded", count=count_row[0])
            return 0

        # Embed rule bodies in batch
        rule_texts = [r["body"] for r in rules]
        logger.info("embedding_rules", count=len(rules))
        embeddings = embedder.embed_texts(rule_texts)

        inserted = 0
        for rule, embedding in zip(rules, embeddings):
            db.execute(
                text("""
                    INSERT INTO compliance_rules
                        (rule_code, rule_type, title, body, embedding, embedded_at)
                    VALUES
                        (:rule_code, :rule_type, :title, :body, CAST(:embedding AS vector), NOW())
                    ON CONFLICT (rule_code) DO NOTHING
                """),
                {
                    "rule_code": rule["rule_code"],
                    "rule_type": rule["rule_type"],
                    "title": rule["title"],
                    "body": rule["body"],
                    "embedding": embedding,
                },
            )
            inserted += 1

    logger.info("rules_seeded", count=inserted)
    return inserted


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    n = seed_rules(force=force)
    print(f"Seeded {n} rules.")
