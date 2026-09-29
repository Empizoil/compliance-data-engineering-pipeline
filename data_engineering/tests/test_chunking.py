from data_engineering.chunking.chunker import TextChunker

def test_chunk_basic_text():
    text = "[CLIENT_1] has an investment account worth [AMOUNT_1]."

    chunker = TextChunker()
    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count > 0


def test_chunk_creates_multiple_overlapping_chunks():
    text = " ".join(["This is compliance text."] * 200)

    chunker = TextChunker()
    chunks = chunker.chunk(text)

    assert len(chunks) > 1

    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1

    assert chunks[0].token_count <= 400
    assert chunks[1].token_count <= 400

def test_chunk_empty_text_returns_empty_list():
    chunker = TextChunker()

    chunks = chunker.chunk("")

    assert chunks == []

def test_chunk_overlap():
    text = " ".join(["This is compliance text."] * 200)

    chunker = TextChunker()
    chunks = chunker.chunk(text)

    assert len(chunks) > 1

    first_chunk = chunks[0]
    second_chunk = chunks[1]

    assert first_chunk.char_end > second_chunk.char_start