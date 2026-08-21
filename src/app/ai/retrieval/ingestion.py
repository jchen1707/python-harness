from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

CHUNKING_VERSION = 1
TARGET_CHUNK_WORDS = 200
CHUNK_OVERLAP_WORDS = 25
MIN_TRAILING_CHUNK_WORDS = 80


@dataclass(frozen=True, slots=True)
class Page:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class Chunk:
    page_number: int
    position: int
    chunking_version: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractionSuccess:
    pages: tuple[Page, ...]


class ExtractionFailureReason(StrEnum):
    NOT_PDF = "not_pdf"
    ENCRYPTED = "encrypted"
    NO_EXTRACTABLE_TEXT = "no_extractable_text"


@dataclass(frozen=True, slots=True)
class ExtractionFailure:
    reason: ExtractionFailureReason


type ExtractionResult = ExtractionSuccess | ExtractionFailure


def chunk_pages(pages: Sequence[Page]) -> tuple[Chunk, ...]:
    """Split pages into ordered chunks."""
    chunks: list[Chunk] = []
    for page in pages:
        words = page.text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(start + TARGET_CHUNK_WORDS, len(words))
            next_start = end - CHUNK_OVERLAP_WORDS
            if end < len(words) and len(words) - next_start < MIN_TRAILING_CHUNK_WORDS:
                end = len(words)
            chunks.append(
                Chunk(
                    page_number=page.page_number,
                    position=len(chunks),
                    chunking_version=CHUNKING_VERSION,
                    text=" ".join(words[start:end]),
                )
            )
            if end == len(words):
                break
            start = next_start
    return tuple(chunks)


def extract_pages(pdf_bytes: bytes) -> ExtractionResult:
    """Extract numbered pages from PDF bytes."""
    if not pdf_bytes.startswith(b"%PDF-"):
        return ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except PdfReadError:
        return ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)

    if reader.is_encrypted:
        return ExtractionFailure(reason=ExtractionFailureReason.ENCRYPTED)

    pages = tuple(
        Page(page_number=page_number, text=page.extract_text().strip())
        for page_number, page in enumerate(reader.pages, start=1)
    )
    if not any(page.text for page in pages):
        return ExtractionFailure(reason=ExtractionFailureReason.NO_EXTRACTABLE_TEXT)

    return ExtractionSuccess(pages=pages)
