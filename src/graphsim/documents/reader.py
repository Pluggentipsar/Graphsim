"""Document reader - extracts text from PDF, DOCX, and TXT files."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class DocumentContent(BaseModel):
    """Extracted content from a document."""

    filename: str
    file_type: str
    text: str
    num_pages: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def preview(self) -> str:
        """First 500 chars of the document."""
        return self.text[:500] + ("..." if len(self.text) > 500 else "")


def read_pdf(file_path: str | Path | None = None, file_bytes: bytes | None = None, filename: str = "document.pdf") -> DocumentContent:
    """Read text from a PDF file."""
    import fitz  # pymupdf

    if file_bytes:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    elif file_path:
        doc = fitz.open(str(file_path))
    else:
        raise ValueError("Provide either file_path or file_bytes")

    pages = []
    for page in doc:
        pages.append(page.get_text())

    text = "\n\n".join(pages)
    num_pages = len(doc)

    metadata = {}
    meta = doc.metadata
    if meta:
        if meta.get("title"):
            metadata["title"] = meta["title"]
        if meta.get("author"):
            metadata["author"] = meta["author"]

    doc.close()

    return DocumentContent(
        filename=filename if file_bytes else Path(file_path).name,
        file_type="pdf",
        text=text.strip(),
        num_pages=num_pages,
        metadata=metadata,
    )


def read_docx(file_path: str | Path | None = None, file_bytes: bytes | None = None, filename: str = "document.docx") -> DocumentContent:
    """Read text from a DOCX file."""
    from io import BytesIO

    import docx

    if file_bytes:
        doc = docx.Document(BytesIO(file_bytes))
    elif file_path:
        doc = docx.Document(str(file_path))
    else:
        raise ValueError("Provide either file_path or file_bytes")

    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)

    metadata = {}
    core = doc.core_properties
    if core.title:
        metadata["title"] = core.title
    if core.author:
        metadata["author"] = core.author

    return DocumentContent(
        filename=filename if file_bytes else Path(file_path).name,
        file_type="docx",
        text=text.strip(),
        metadata=metadata,
    )


def read_txt(file_path: str | Path | None = None, file_bytes: bytes | None = None, filename: str = "document.txt") -> DocumentContent:
    """Read text from a plain text file."""
    if file_bytes:
        text = file_bytes.decode("utf-8", errors="replace")
    elif file_path:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        raise ValueError("Provide either file_path or file_bytes")

    return DocumentContent(
        filename=filename if file_bytes else Path(file_path).name,
        file_type="txt",
        text=text.strip(),
    )


def read_document(
    file_path: str | Path | None = None,
    file_bytes: bytes | None = None,
    filename: str = "document",
) -> DocumentContent:
    """Read a document, auto-detecting format from extension."""
    if file_path:
        ext = Path(file_path).suffix.lower()
    elif filename:
        ext = Path(filename).suffix.lower()
    else:
        raise ValueError("Cannot detect file type")

    readers = {
        ".pdf": read_pdf,
        ".docx": read_docx,
        ".doc": read_docx,
        ".txt": read_txt,
        ".md": read_txt,
    }

    reader = readers.get(ext)
    if not reader:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {', '.join(readers.keys())}")

    return reader(file_path=file_path, file_bytes=file_bytes, filename=filename)
