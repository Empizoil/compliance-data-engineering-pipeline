from data_engineering.masking.masker import PIIMasker
from data_engineering.masking.entity_types import EntityType


def test_mask_basic_pii():
    text = """
    John Smith
    john.smith@example.com
    $50,000
    123456789012
    """

    result = PIIMasker().mask(text)

    assert "[CLIENT_1]" in result.masked_text
    assert "[EMAIL_1]" in result.masked_text
    assert "[AMOUNT_1]" in result.masked_text
    assert "[ACCOUNT_1]" in result.masked_text

def test_repeated_pii_uses_same_placeholder():
    text = """
    John Smith contacted us.
    John Smith has an investment account.
    """

    result = PIIMasker().mask(text)

    assert result.masked_text.count("[CLIENT_1]") == 2
    assert result.mapping["[CLIENT_1]"] == "John Smith"

def test_entity_counts():
    text = """
    John Smith
    john.smith@example.com
    $50,000
    123456789012
    """

    result = PIIMasker().mask(text)

    assert result.entity_counts[EntityType.NAME] == 1
    assert result.entity_counts[EntityType.EMAIL] == 1
    assert result.entity_counts[EntityType.DOLLAR_AMOUNT] == 1
    assert result.entity_counts[EntityType.ACCOUNT] == 1

    print("MASKED TEXT:")
    print(result.masked_text)

    print("MAPPING:")
    print(result.mapping)

    print("COUNTS:")
    print(result.entity_counts)