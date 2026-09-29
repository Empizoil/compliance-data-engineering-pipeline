import re
import structlog
from dataclasses import dataclass, field
from .patterns import PATTERNS
from .entity_types import EntityType

logger = structlog.get_logger(__name__)


@dataclass
class MaskingResult:
    masked_text: str
    # Maps placeholder -> original value, e.g. {"[CLIENT_1]": "John Smith"}
    mapping: dict[str, str]
    # Reverse map for fast lookup: original -> placeholder
    entity_counts: dict[EntityType, int] = field(default_factory=dict)


class PIIMasker:
    """
    Server-side PII masking engine.

    Replaces PII with stable, typed placeholders using regex and heuristics.
    The same original value always maps to the same placeholder within a masking run,
    enabling coherent reasoning over masked text.

    This is a HEURISTIC masker — not a production NER system.
    See patterns.py for documented limitations.
    """

    def __init__(self):
        self._patterns = PATTERNS

    def mask(self, text: str) -> MaskingResult:
        """
        Mask all PII in text. Returns masked text and the placeholder mapping.
        Thread-safe — creates fresh state per call.
        """
        # Track unique originals to assign stable placeholders
        # original_value -> placeholder
        original_to_placeholder: dict[str, str] = {}
        # Counter per entity type: {"NAME": 1, "EMAIL": 1, ...}
        counters: dict[str, int] = {}

        # Build a list of all matches across all patterns
        # Each: (start, end, original_text, entity_type)
        matches: list[tuple[int, int, str, EntityType]] = []

        for pattern, entity_type in self._patterns:
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end(), m.group(), entity_type))

        # Sort by start position, then by length descending (prefer longer matches)
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        # Resolve overlaps — keep the first (longest at each position)
        resolved: list[tuple[int, int, str, EntityType]] = []
        last_end = -1
        for start, end, original, entity_type in matches:
            if start >= last_end:
                resolved.append((start, end, original, entity_type))
                last_end = end

        # Assign placeholders and build replacement map
        # segment -> placeholder for this text
        span_replacements: list[tuple[int, int, str]] = []
        entity_counts: dict[EntityType, int] = {}

        for start, end, original, entity_type in resolved:
            if original not in original_to_placeholder:
                type_key = entity_type.value
                counters[type_key] = counters.get(type_key, 0) + 1
                n = counters[type_key]

                # Build readable placeholder names
                label_map = {
                    EntityType.NAME: "CLIENT",
                    EntityType.EMAIL: "EMAIL",
                    EntityType.PHONE: "PHONE",
                    EntityType.ADDRESS: "ADDRESS",
                    EntityType.ACCOUNT: "ACCOUNT",
                    EntityType.SSN: "SSN",
                    EntityType.DOLLAR_AMOUNT: "AMOUNT",
                }
                label = label_map.get(entity_type, entity_type.value)
                placeholder = f"[{label}_{n}]"
                original_to_placeholder[original] = placeholder

            placeholder = original_to_placeholder[original]
            span_replacements.append((start, end, placeholder))
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        # Build masked text by substituting spans in reverse order
        masked_text = text
        for start, end, placeholder in sorted(
            span_replacements, key=lambda x: x[0], reverse=True
        ):
            masked_text = masked_text[:start] + placeholder + masked_text[end:]

        # Invert map for storage: placeholder -> original
        placeholder_to_original = {
            v: k for k, v in original_to_placeholder.items()
        }

        logger.info(
            "masking_complete",
            total_entities_masked=len(resolved),
            entity_counts={k.value: v for k, v in entity_counts.items()},
        )

        return MaskingResult(
            masked_text=masked_text,
            mapping=placeholder_to_original,
            entity_counts=entity_counts,
        )