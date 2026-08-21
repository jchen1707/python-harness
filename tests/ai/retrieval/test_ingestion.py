from io import BytesIO
from statistics import mean

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

from app.ai.retrieval.ingestion import (
    Chunk,
    ExtractionFailure,
    ExtractionFailureReason,
    ExtractionSuccess,
    Page,
    chunk_pages,
    extract_pages,
)


def _pdf_bytes(*page_texts: str) -> bytes:
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for page_text in page_texts:
        pdf.add_page()
        pdf.multi_cell(w=0, h=5, text=page_text)
    return bytes(pdf.output())


def _encrypted_pdf_bytes(page_text: str) -> bytes:
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(_pdf_bytes(page_text))))
    writer.encrypt("test-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _words(count: int, *, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{index:03d}" for index in range(count))


def test_extract_pages_returns_numbered_pages_in_order() -> None:
    result = extract_pages(_pdf_bytes("First page text.", "Second page text."))

    assert result == ExtractionSuccess(
        pages=(
            Page(number=1, text="First page text."),
            Page(number=2, text="Second page text."),
        )
    )


def test_extract_pages_reports_non_pdf_input() -> None:
    result = extract_pages(b"This is not a PDF.")

    assert result == ExtractionFailure(reason=ExtractionFailureReason.NOT_PDF)


def test_extract_pages_reports_encrypted_pdf() -> None:
    result = extract_pages(_encrypted_pdf_bytes("Protected text."))

    assert result == ExtractionFailure(reason=ExtractionFailureReason.ENCRYPTED)


def test_extract_pages_reports_pdf_without_extractable_text() -> None:
    result = extract_pages(_pdf_bytes(""))

    assert result == ExtractionFailure(reason=ExtractionFailureReason.NO_EXTRACTABLE_TEXT)


def test_chunk_pages_keeps_a_short_page_in_one_chunk() -> None:
    page_text = "one two three four five six seven eight nine ten"

    chunks = chunk_pages((Page(number=3, text=page_text),))

    assert chunks == (
        Chunk(
            page_number=3,
            position=0,
            text=page_text,
            chunking_version="1",
        ),
    )


def test_chunk_pages_targets_200_words() -> None:
    chunks = chunk_pages((Page(number=1, text=_words(375)),))

    assert tuple(len(chunk.text.split()) for chunk in chunks) == (200, 200)


def test_chunk_pages_average_stays_near_200_words() -> None:
    chunks = chunk_pages((Page(number=1, text=_words(750)),))

    average_words = mean(len(chunk.text.split()) for chunk in chunks)
    assert 185 <= average_words <= 215


def test_chunk_pages_merges_a_short_trailing_chunk() -> None:
    chunks = chunk_pages((Page(number=1, text=_words(420)),))

    assert tuple(len(chunk.text.split()) for chunk in chunks) == (200, 245)


def test_chunk_pages_overlaps_adjacent_chunks_by_25_words() -> None:
    chunks = chunk_pages((Page(number=1, text=_words(375)),))

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-25:] == second_words[:25]


def test_pdf_pipeline_never_crosses_a_page_boundary() -> None:
    result = extract_pages(
        _pdf_bytes(
            _words(260, prefix="first"),
            _words(260, prefix="second"),
        )
    )
    assert isinstance(result, ExtractionSuccess)

    chunks = chunk_pages(result.pages)

    page_content = tuple(
        (
            chunk.page_number,
            frozenset(word.rstrip("0123456789") for word in chunk.text.split()),
        )
        for chunk in chunks
    )
    assert page_content == (
        (1, frozenset({"first"})),
        (1, frozenset({"first"})),
        (2, frozenset({"second"})),
        (2, frozenset({"second"})),
    )


def test_chunk_pages_records_metadata_on_every_chunk() -> None:
    chunks = chunk_pages(
        (
            Page(number=4, text=_words(375)),
            Page(number=8, text="final page"),
        )
    )

    assert tuple(
        (chunk.page_number, chunk.position, chunk.chunking_version) for chunk in chunks
    ) == ((4, 0, "1"), (4, 1, "1"), (8, 2, "1"))
