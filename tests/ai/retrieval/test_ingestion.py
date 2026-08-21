from io import BytesIO

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

from app.ai.retrieval.ingestion import (
    ExtractionFailure,
    ExtractionFailureReason,
    ExtractionSuccess,
    Page,
    chunk_pages,
    extract_pages,
)


def _pdf_bytes(*page_texts: str) -> bytes:
    pdf = FPDF(unit="pt", format=(2_000, 2_000))
    pdf.set_auto_page_break(auto=False)
    for page_text in page_texts:
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.multi_cell(w=0, h=16, text=page_text)
    return bytes(pdf.output())


def _encrypted_pdf_bytes(page_text: str) -> bytes:
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(_pdf_bytes(page_text))))
    writer.encrypt("test-password")
    encrypted_pdf = BytesIO()
    writer.write(encrypted_pdf)
    return encrypted_pdf.getvalue()


def _words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{index:03d}" for index in range(count))


def _extracted_pages(*page_texts: str) -> tuple[Page, ...]:
    result = extract_pages(_pdf_bytes(*page_texts))
    if isinstance(result, ExtractionFailure):
        raise AssertionError(result.reason)
    return result.pages


def test_extract_pages_returns_ordered_numbered_pages() -> None:
    result = extract_pages(_pdf_bytes("First page text.", "Second page text."))

    assert result == ExtractionSuccess(
        pages=(
            Page(page_number=1, text="First page text."),
            Page(page_number=2, text="Second page text."),
        )
    )


def test_extract_pages_reports_non_pdf_bytes() -> None:
    result = extract_pages(b"This is not a PDF.")

    assert result == ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)


def test_extract_pages_reports_pdf_bytes_without_a_pdf_header() -> None:
    pdf_bytes = _pdf_bytes("Readable text.")
    bytes_without_pdf_header = b"XXXXX" + pdf_bytes[5:]

    result = extract_pages(bytes_without_pdf_header)

    assert result == ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)


def test_extract_pages_reports_encrypted_pdf() -> None:
    result = extract_pages(_encrypted_pdf_bytes("Protected text."))

    assert result == ExtractionFailure(reason=ExtractionFailureReason.ENCRYPTED)


def test_extract_pages_reports_pdf_without_extractable_text() -> None:
    result = extract_pages(_pdf_bytes(""))

    assert result == ExtractionFailure(reason=ExtractionFailureReason.NO_EXTRACTABLE_TEXT)


def test_chunk_pages_keeps_a_short_page_in_one_chunk() -> None:
    text = _words("short", 50)

    chunks = chunk_pages((Page(page_number=3, text=text),))

    assert [chunk.text for chunk in chunks] == [text]


def test_chunk_pages_targets_approximately_200_words() -> None:
    page = Page(page_number=1, text=_words("target", 375))

    chunks = chunk_pages((page,))

    assert [len(chunk.text.split()) for chunk in chunks] == [200, 200]


def test_chunk_pages_overlaps_adjacent_chunks_within_a_page() -> None:
    page = Page(page_number=1, text=_words("overlap", 375))

    first, second = chunk_pages((page,))

    assert first.text.split()[-25:] == second.text.split()[:25]


def test_chunk_pages_keeps_uneven_chunks_near_the_word_target() -> None:
    page = Page(page_number=1, text=_words("uneven", 334))

    chunks = chunk_pages((page,))

    assert [len(chunk.text.split()) for chunk in chunks] == [200, 159]


def test_chunk_pages_merges_a_short_trailing_chunk_into_the_previous_chunk() -> None:
    page = Page(page_number=1, text=_words("merge", 400))

    chunks = chunk_pages((page,))

    assert [len(chunk.text.split()) for chunk in chunks] == [200, 225]


def test_pdf_chunks_never_cross_a_page_boundary() -> None:
    pages = _extracted_pages(_words("first", 375), _words("second", 375))

    chunks = chunk_pages(pages)

    assert [
        (chunk.page_number, {word[:-3] for word in chunk.text.split()}) for chunk in chunks
    ] == [
        (1, {"first"}),
        (1, {"first"}),
        (2, {"second"}),
        (2, {"second"}),
    ]


def test_chunk_pages_records_positions_in_document_order() -> None:
    pages = (
        Page(page_number=1, text=_words("first", 375)),
        Page(page_number=2, text=_words("second", 375)),
    )

    chunks = chunk_pages(pages)

    assert [chunk.position for chunk in chunks] == [0, 1, 2, 3]


def test_chunk_pages_records_the_chunking_version() -> None:
    page = Page(page_number=1, text=_words("version", 375))

    chunks = chunk_pages((page,))

    assert [chunk.chunking_version for chunk in chunks] == [1, 1]
