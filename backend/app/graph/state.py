from typing import TypedDict, List, Dict, Optional

class RAGState(TypedDict, total=False):
    request_id: str  # request context identifier
    question: str
    history: List[Dict[str, str]]
    use_documents: bool
    standalone: str  # rewritten question (or original)
    hits: List[Dict]
    context: str
    sources: List[Dict]
    answer: str
    relevant: bool
    retries: int
