/** Shared UI + upload limits (mirror backend defaults). */
export const MAX_UPLOAD_MB = 10;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
export const MAX_MESSAGE_CHARS = 4000;
export const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md"] as const;
export const ACCEPT_ATTR = ".pdf,.txt,.md";

/** Fixed width of the centered chat column (px). */
export const CHAT_COLUMN_WIDTH_PX = 768;

export const EXAMPLE_PROMPTS = [
  "What is a virtual environment and how do I create one?",
  "How does Retrieval-Augmented Generation work?",
  "What is the difference between a list and a tuple?",
] as const;