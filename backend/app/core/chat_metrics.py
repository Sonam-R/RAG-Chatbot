from dataclasses import dataclass, field


@dataclass
class ChatRequestMetrics:
    conversation_id: str
    use_documents: bool
    question_chars: int
    rewritten_question: str | None = None
    chunks_before: list[dict] = field(default_factory=list)
    chunks_after: list[dict] = field(default_factory=list)
    prompt_chars: int = 0
    answer_chars: int = 0
    rewrite_s: float | None = None
    embed_s: float | None = None
    search_s: float | None = None
    first_token_s: float | None = None
    total_s: float | None = None
    outcome: str = "ok"

    def to_log_dict(self, request_id: str) -> dict:
        return {
            "request_id": request_id,
            "conversation_id": self.conversation_id,
            "use_documents": self.use_documents,
            "question_chars": self.question_chars,
            "rewritten_question": (self.rewritten_question or "")[:200],
            "chunks_before": self.chunks_before,
            "chunks_after": self.chunks_after,
            "prompt_chars": self.prompt_chars,
            "answer_chars": self.answer_chars,
            "rewrite_s": self.rewrite_s,
            "embed_s": self.embed_s,
            "search_s": self.search_s,
            "first_token_s": self.first_token_s,
            "total_s": self.total_s,
            "outcome": self.outcome,
        }