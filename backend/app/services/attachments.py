"""Extract text from an attached BRD or requirement document."""
import io

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 60_000
SUPPORTED = (".txt", ".md", ".csv", ".json", ".xml", ".docx", ".pdf")


class AttachmentError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if len(data) > MAX_BYTES:
        raise AttachmentError(f"{filename} is larger than 5 MB.")
    if not name.endswith(SUPPORTED):
        raise AttachmentError(f"{filename}: attach a .docx, .pdf, .txt or .md file.")
    try:
        if name.endswith(".docx"):
            from docx import Document

            doc = Document(io.BytesIO(data))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
            text = "\n".join(parts)
        elif name.endswith(".pdf"):
            from pypdf import PdfReader

            text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
        else:
            text = data.decode("utf-8", errors="replace")
    except AttachmentError:
        raise
    except Exception as e:  # noqa: BLE001  (corrupt or encrypted files)
        raise AttachmentError(f"Couldn't read {filename}. Is it a valid, unprotected file?") from e
    text = text.strip()
    if not text:
        raise AttachmentError(f"{filename} has no readable text. Scanned PDFs aren't supported yet.")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[… document truncated]"
    return text
