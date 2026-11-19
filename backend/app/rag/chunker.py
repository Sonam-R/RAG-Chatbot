import tiktoken

# Create a single encoder instance at module load time – this is cheap and reused for every call.
_enc = tiktoken.get_encoding("cl100k_base")

def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size to create a forward moving window")

    tokens = _enc.encode(text)
    step = size - overlap
    chunks: list[str] = []
    for start in range(0, len(tokens), step):
        # Slice the token window – it may be shorter at the very end, but we stop early
        # to avoid a tiny trailing chunk (see the break condition below).
        chunk_tokens = tokens[start:start + size]
        chunks.append(_enc.decode(chunk_tokens))
        if start + size >= len(tokens):
            break
    return chunks
