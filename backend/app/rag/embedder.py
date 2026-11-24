from app.core.config import settings
from app.llm.provider import client

# Number of texts to send in a single request to the embedding endpoint.
BATCH = 32

async def embed_texts(texts: list[str], prefix: str = "") -> list[list[float]]:
    """Convert a list of strings into embedding vectors using the shared LLM client.

    Parameters
    ----------
    texts: list[str]
        Texts (e.g., document chunks or a query) to embed.
    prefix: str, default=""
        Optional prefix that is concatenated to the beginning of each text before
        sending it to the model (e.g., "search_document: " or "search_query: ").

    Returns
    -------
    list[list[float]]
        A list of embedding vectors in the same order as the input ``texts``.
    """
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = [prefix + t for t in texts[i:i + BATCH]]
        # The OpenAI/Ollama client exposes an ``embeddings`` namespace.
        resp = await client.embeddings.create(
            model=settings.embed_model,
            input=batch,
            extra_body={"keep_alive": settings.ollama_keep_alive},
        )
        out.extend(d.embedding for d in resp.data)
    return out
