from data_engineering.masking.unmasker import unmask_text


def test_unmask_text():
    masked_text = "[CLIENT_1] has an investment of [AMOUNT_1]."

    mapping = {
        "[CLIENT_1]": "John Smith",
        "[AMOUNT_1]": "$50,000",
    }

    result = unmask_text(masked_text, mapping)

    assert result == "John Smith has an investment of $50,000."

def test_unmask_placeholder_order():
    masked_text = "[CLIENT_10] and [CLIENT_1]"

    mapping = {
        "[CLIENT_1]": "John Smith",
        "[CLIENT_10]": "Jane Smith",
    }

    result = unmask_text(masked_text, mapping)

    assert result == "Jane Smith and John Smith"