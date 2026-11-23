import hashlib
import io
import logging
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.rag.chunker import chunk_text
from app.rag.embedder import embed_texts
from app.rag.vector_store import add_chunks, delete_document, search as vector_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
ALLOWED = {".pdf", ".txt", ".md"}

def extract_pages(ext: str, data: bytes) -> list[tuple[int, str]]:
    """Extract page number and text from a file.
    Returns a list of (page_number, text) tuples, dropping empty pages.
    """
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [(i + 1, (p.extract_text() or "").strip()) for i, p in enumerate(reader.pages)]
    else:
        text = data.decode("utf-8", errors="ignore").strip()
        pages = [(1, text)]
    return [(n, t) for n, t in pages if t]

@router.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail="Only PDF, TXT and MD files are supported")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File larger than {settings.max_upload_mb} MB")

    try:
        pages = await run_in_threadpool(extract_pages, ext, data)
    except Exception:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(status_code=422, detail="Could not read the file (corrupt or encrypted?)")
    if not pages:
        raise HTTPException(status_code=422, detail="No extractable text found (scanned PDFs are not supported yet)")

    # Derive the id from the file content so re-uploading the same file replaces
    # the old chunks instead of creating duplicates.
    doc_id = hashlib.sha256(data).hexdigest()[:32]
    texts: list[str] = []
    metadatas: list[dict] = []
    for page_no, page_text in pages:
        chunks = chunk_text(page_text, settings.chunk_size, settings.chunk_overlap)
        for idx, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "filename": file.filename,
                "page": page_no,
                "chunk_index": idx,
            })

    try:
        embeddings = await embed_texts(texts, prefix="search_document: ")
    except Exception:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=502, detail="Embedding service unavailable")
    ids = [f"{doc_id}-{i}" for i in range(len(texts))]
    await run_in_threadpool(delete_document, doc_id)  # drop any earlier upload of the same file
    await run_in_threadpool(add_chunks, ids, texts, embeddings, metadatas)
    return {"doc_id": doc_id, "filename": file.filename, "pages": len(pages), "chunks": len(texts)}

@router.get("/search")
async def search_documents(q: str = Query(..., min_length=1), k: int | None = Query(None, ge=1, le=50)):
    try:
        query_emb = (await embed_texts([q], prefix="search_query: "))[0]
    except Exception:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=502, detail="Embedding service unavailable")
    return await run_in_threadpool(vector_search, query_emb, k or settings.top_k)

@router.delete("/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    delete_document(doc_id)
    return {"deleted": doc_id}
