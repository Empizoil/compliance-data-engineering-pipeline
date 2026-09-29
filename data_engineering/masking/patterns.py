import re
from .entity_types import EntityType

# Each entry: (compiled regex, EntityType, group_index_for_match)
# Patterns are ordered by specificity — more specific patterns first
# to avoid partial matches overriding more complete ones.

PATTERNS: list[tuple[re.Pattern, EntityType]] = [
    # SSN — must come before generic number patterns
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        EntityType.SSN,
    ),
    # Account numbers (10–18 digit sequences, optionally hyphenated)
    (
        re.compile(r"\b(?:account|acct|acc)[\s#.:]*([A-Z0-9]{8,18})\b", re.IGNORECASE),
        EntityType.ACCOUNT,
    ),
    (
        re.compile(r"\b\d{10,18}\b"),
        EntityType.ACCOUNT,
    ),
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
        EntityType.EMAIL,
    ),
    # US phone numbers — various formats
    (
        re.compile(
            r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
        ),
        EntityType.PHONE,
    ),
    # Dollar amounts tied to a person (e.g. "John's $250,000 portfolio")
    # Capture dollar amounts: $1,234 / $1,234.56 / $1M / USD 1,234
    (
        re.compile(r"\$[\d,]+(?:\.\d{1,2})?(?:[KMB])?\b|USD\s*[\d,]+(?:\.\d{1,2})?"),
        EntityType.DOLLAR_AMOUNT,
    ),
    # US street addresses
    (
        re.compile(
            r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s){1,3}"
            r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)"
            r"(?:\s+(?:Apt|Suite|Unit|#)\s*\w+)?"
            r"(?:,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?\b",
            re.IGNORECASE,
        ),
        EntityType.ADDRESS,
    ),
    # Full names — Title Case two-word minimum with optional title prefix
    # NOTE: This is heuristic and will miss non-Western names. Document this limitation.
    (
        re.compile(
            r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)?\s*"
            r"(?:[A-Z][a-z]{1,20}\s){1,2}[A-Z][a-z]{1,20}\b"
        ),
        EntityType.NAME,
    ),
]