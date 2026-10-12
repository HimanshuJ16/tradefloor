"""Isolated, time-bounded PDF text extraction worker; no OCR or embedded-code execution."""
import io
import json
import sys

from pypdf import PdfReader


def extract(raw):
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted or len(reader.pages) > 200:
        raise ValueError("Use an unencrypted PDF with at most 200 pages")
    pieces, count = [], 0
    for page in reader.pages:
        contents = page.get_contents()
        if contents is not None and len(contents.get_data()) > 2_000_000:
            raise ValueError("PDF page content exceeds the extraction limit")
        body = page.extract_text() or ""
        count += len(body) + 2
        if count > 200_000:
            raise ValueError("Extracted PDF text exceeds 200,000 characters")
        pieces.append(body)
    body = "\n\n".join(pieces)
    if not body.strip():
        raise ValueError("PDF has no extractable text; OCR is not included")
    return {"text": body, "pages": len(reader.pages)}


if __name__ == "__main__":
    try:
        raw = sys.stdin.buffer.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("PDF exceeds 5 MB")
        print(json.dumps(extract(raw), ensure_ascii=True))
    except Exception:
        print(json.dumps({"error": "PDF extraction failed: encrypted, scanned, malformed or over the bounded extraction limits. Import a verified text transcription instead."}))
        sys.exit(1)
