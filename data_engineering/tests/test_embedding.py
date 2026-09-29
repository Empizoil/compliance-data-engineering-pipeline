from data_engineering.embedding.embedder import EmbeddingClient


def test_embed_texts_empty_input():
    client = EmbeddingClient()

    result = client.embed_texts([])

    assert result == []

def test_embed_texts_batches_correctly():
    client = EmbeddingClient()

    client._embed_batch = lambda texts: [
        [float(i)] * 768 for i in range(len(texts))
    ]

    texts = [f"text {i}" for i in range(45)]

    result = client.embed_texts(texts)

    assert len(result) == 45

def test_embed_texts_preserves_order():
    client = EmbeddingClient()

    client._embed_batch = lambda texts: [
        [float(i)] * 768 for i in range(len(texts))
    ]

    texts = ["first", "second", "third"]

    result = client.embed_texts(texts)

    assert len(result) == 3
    assert result[0][0] == 0.0
    assert result[1][0] == 1.0
    assert result[2][0] == 2.0

def test_embed_batch_rejects_wrong_dimension():
    client = EmbeddingClient()

    client._model = "test-model"
    client._dimension = 768

    # Simulate an embedding with the wrong dimension.
    import data_engineering.embedding.embedder as embedder_module

    original_embed_content = embedder_module.genai.embed_content

    try:
        embedder_module.genai.embed_content = lambda **kwargs: {
            "embedding": [[0.0] * 10]
        }

        try:
            client._embed_batch(["test text"])
            assert False, "Expected ValueError for incorrect embedding dimension"
        except ValueError as e:
            assert "expected 768" in str(e)
    finally:
        embedder_module.genai.embed_content = original_embed_content