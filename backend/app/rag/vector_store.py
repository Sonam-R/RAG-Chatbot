import chromadb
from app.core.config import settings

# Persistent Chroma client and collection (created once)
_client = chromadb.PersistentClient(path=settings.chroma_path)
_collection = _client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"},
)

# Add chunk records (ids, texts, embeddings, metadatas) to collection
def add_chunks(ids, texts, embeddings, metadatas) -> None:
    _collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

# Search collection with query embedding and return top‑k hits
def search(query_embedding: list[float], k: int) -> list[dict]:
    res = _collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits: list[dict] = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({
            "text": doc,
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "score": round(1 - dist, 4),  # cosine similarity
        })
    return hits

# Delete all chunks belonging to a document identified by doc_id
def delete_document(doc_id: str) -> None:
    _collection.delete(where={"doc_id": doc_id})
