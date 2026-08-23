"""Generate the Meridian mock PDF corpus from committed JSON text."""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fpdf import FPDF
from pydantic import BaseModel, ConfigDict, Field, field_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "meridian" / "documents.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "meridian-corpus"
CREATION_DATE = datetime(2026, 8, 23, tzinfo=UTC)
BRAND_COLOURS = ((30, 73, 118), (45, 97, 86), (83, 67, 120), (112, 72, 38))


class SourceDocument(BaseModel):
    """One document in the committed source file."""

    model_config = ConfigDict(extra="forbid")

    id: str
    file_name: str
    visibility: Literal["external", "internal"]
    title: str
    context: str
    pages: list[str] = Field(min_length=4, max_length=6)

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        """Require a plain PDF file name."""
        if Path(value).name != value or Path(value).suffix.casefold() != ".pdf":
            raise ValueError("file_name must be a plain PDF file name")
        return value


class CorpusSource(BaseModel):
    """The committed input used to create all PDFs."""

    model_config = ConfigDict(extra="forbid")

    seed: int
    documents: list[SourceDocument]


def _load_source(source_path: Path) -> CorpusSource:
    """Load the committed JSON source."""
    return CorpusSource.model_validate_json(source_path.read_text(encoding="utf-8"))


def _write_pdf(document: SourceDocument, path: Path, colour: tuple[int, int, int]) -> None:
    """Write one deterministic PDF from a source document."""
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_creation_date(CREATION_DATE)
    pdf.set_title(document.title)
    pdf.set_author("Meridian Support")
    pdf.set_creator("Meridian mock corpus generator")
    pdf.set_subject(document.visibility)
    pdf.set_auto_page_break(auto=False)

    for page_number, page_text in enumerate(document.pages, start=1):
        pdf.add_page()
        pdf.set_fill_color(*colour)
        pdf.rect(0, 0, 210, 8, style="F")
        pdf.set_xy(20, 18)
        pdf.set_text_color(*colour)
        pdf.set_font("Helvetica", style="B", size=17)
        pdf.multi_cell(170, 8, document.title)
        pdf.ln(2)
        pdf.set_text_color(70, 70, 70)
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 5, f"Meridian Support | {document.visibility.title()} | Page {page_number}")
        pdf.ln(9)
        pdf.set_text_color(25, 25, 25)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(170, 6, f"{document.context}\n\n{page_text}", align="L")

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(path)


def generate_corpus(source_path: Path, output_dir: Path) -> list[Path]:
    """Generate all corpus PDFs and return their paths in source order."""
    source = _load_source(source_path)
    randomizer = random.Random(source.seed)  # noqa: S311 - Visual selection needs no security.
    paths: list[Path] = []

    for document in source.documents:
        colour = BRAND_COLOURS[randomizer.randrange(len(BRAND_COLOURS))]
        path = output_dir / document.visibility / document.file_name
        _write_pdf(document, path, colour)
        paths.append(path)

    return paths


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    """Generate the corpus for command-line use."""
    args = _parse_args()
    paths = generate_corpus(args.source, args.output)
    print(f"Generated {len(paths)} PDFs in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
