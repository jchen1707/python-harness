from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True, slots=True)
class Page:
    number: int
    text: str


@dataclass(frozen=True, slots=True)
class Chunk:
    page_number: int
    position: int
    text: str
    chunking_version: str


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

_CHUNKING_VERSION = "1"
_CHUNK_SIZE_WORDS = 200
_CHUNK_OVERLAP_WORDS = 25
_MIN_TRAILING_CHUNK_WORDS = 80


def extract_pages(pdf_bytes: bytes) -> ExtractionResult:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except PdfReadError:
        return ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)
    if reader.is_encrypted:
        return ExtractionFailure(reason=ExtractionFailureReason.ENCRYPTED)

    pages = tuple(
        Page(number=page_number, text=(page.extract_text() or "").strip())
        for page_number, page in enumerate(reader.pages, start=1)
    )
    if not any(page.text for page in pages):
        return ExtractionFailure(reason=ExtractionFailureReason.NO_EXTRACTABLE_TEXT)
    return ExtractionSuccess(pages=pages)


def chunk_pages(pages: Sequence[Page]) -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []
    step = _CHUNK_SIZE_WORDS - _CHUNK_OVERLAP_WORDS
    for page in pages:
        words = page.text.split()
        page_chunks: list[list[str]] = []
        for start in range(0, len(words), step):
            page_chunks.append(words[start : start + _CHUNK_SIZE_WORDS])
            if start + _CHUNK_SIZE_WORDS >= len(words):
                break
        if len(page_chunks) > 1 and len(page_chunks[-1]) < _MIN_TRAILING_CHUNK_WORDS:
            page_chunks[-2].extend(page_chunks[-1][_CHUNK_OVERLAP_WORDS:])
            page_chunks.pop()
        for chunk_words in page_chunks:
            chunks.append(
                Chunk(
                    page_number=page.number,
                    position=len(chunks),
                    text=" ".join(chunk_words),
                    chunking_version=_CHUNKING_VERSION,
                )
            )
    return tuple(chunks)
