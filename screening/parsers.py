"""Resume text extraction (Module 5)."""
import io
from pathlib import Path


class ResumeParseError(Exception):
    pass


def extract_text(file_obj, filename):
    """Return the plain text of a PDF, DOCX or TXT resume.

    `file_obj` is any binary file-like object. Raises ResumeParseError when the
    file cannot be read or contains no text.
    """
    ext = Path(filename).suffix.lower()
    data = file_obj.read()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            import docx

            document = docx.Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
        elif ext == ".txt":
            text = data.decode("utf-8", errors="ignore")
        else:
            raise ResumeParseError(f"Unsupported file type: {ext}")
    except ResumeParseError:
        raise
    except Exception as exc:  # corrupt or password-protected files
        raise ResumeParseError("Could not read the resume file. Please upload a valid PDF, DOCX or TXT.") from exc

    text = " ".join(text.split())
    if len(text) < 30:
        raise ResumeParseError("No readable text was found in the resume. Scanned images are not supported.")
    return text
