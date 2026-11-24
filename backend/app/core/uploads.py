import re
from pathlib import Path


def sanitize_filename(name: str | None) -> str:
    """Keep only a safe display label; never use as a filesystem path."""
    if not name:
        return "upload"
    base = Path(name).name
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    if not cleaned:
        return "upload"
    return cleaned[:255]