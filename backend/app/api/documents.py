import hashlib
import io
import logging
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.db.models import Document
from app.db.session import SessionLocal
from app.rag.chunker import chunk_text
from app.rag.embedder import embed_texts
from app.rag.vector_store import add_chunks, delete_document, search as vector_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
ALLOWED = {".pdf", ".txt", ".md"}


class DocumentOut(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int
    created_at: str

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
    try:
        await run_in_threadpool(delete_document, doc_id)  # drop any earlier upload of the same file
        await run_in_threadpool(add_chunks, ids, texts, embeddings, metadatas)
    except Exception:
        logger.exception("Failed to store document vectors")
        raise HTTPException(status_code=502, detail="Failed to store document vectors")

    db = SessionLocal()
    try:
        row = db.query(Document).filter(Document.id == doc_id).first()
        if row:
            row.filename = file.filename or ""
            row.pages = len(pages)
            row.chunks = len(texts)
        else:
            db.add(
                Document(
                    id=doc_id,
                    filename=file.filename or "",
                    pages=len(pages),
                    chunks=len(texts),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to save document metadata")
        try:
            delete_document(doc_id)
        except Exception:
            logger.exception("Failed to roll back vectors after a metadata error")
        raise HTTPException(status_code=500, detail="Failed to save document metadata")
    finally:
        db.close()

    return {"doc_id": doc_id, "filename": file.filename, "pages": len(pages), "chunks": len(texts)}

@router.get("/search")
async def search_documents(q: str = Query(..., min_length=1), k: int | None = Query(None, ge=1, le=50)):
    try:
        query_emb = (await embed_texts([q], prefix="search_query: "))[0]
    except Exception:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=502, detail="Embedding service unavailable")
    return await run_in_threadpool(vector_search, query_emb, k or settings.top_k)

@router.get("/documents", response_model=list[DocumentOut])
def list_documents():
    db = SessionLocal()
    try:
        rows = db.query(Document).order_by(Document.created_at.desc()).all()
        return [
            DocumentOut(
                id=r.id,
                filename=r.filename,
                pages=r.pages,
                chunks=r.chunks,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]
    finally:
        db.close()


@router.delete("/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    db = SessionLocal()
    try:
        row = db.query(Document).filter(Document.id == doc_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        try:
            delete_document(doc_id)
        except Exception:
            logger.exception("Failed to delete document vectors")
            raise HTTPException(status_code=502, detail="Failed to delete document vectors")
        db.delete(row)
        db.commit()
        return {"deleted": doc_id}
    finally:
        db.close()
