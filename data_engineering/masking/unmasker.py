import re

def unmask_text(masked_text: str, mapping: dict[str, str]) -> str:
    """
    Replace placeholders with original values for officer display.

    mapping: {placeholder: original_value}
    e.g. {"[CLIENT_1]": "John Smith", "[EMAIL_1]": "john@example.com"}

    This is ONLY called when rendering text for the officer UI.
    Never called before sending to the LLM or embedding API.
    """
    result = masked_text
    # Sort by placeholder length descending to avoid partial substitution
    # e.g. [CLIENT_10] before [CLIENT_1]
    for placeholder, original in sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True):
        result = result.replace(placeholder, original)
    return result