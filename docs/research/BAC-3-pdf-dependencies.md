# BAC-3 PDF dependency research

Research date: 2026-08-21.

## Recommendation

- Use `pypdf>=6.16` for PDF reading and text extraction.
- Use `fpdf2>=2.8` for PDF generation.

These bounds match the repository's minor-version floor style.
See the current bounds in [`pyproject.toml`](../../pyproject.toml).

The lock resolves pypdf 6.16.1 and fpdf2 2.8.8.
See the resolved packages in [`uv.lock`](../../uv.lock).

## Capability evidence

The pypdf 6.16.1 example opens a PDF with `PdfReader`.
It counts `reader.pages`, selects a page, and calls `extract_text()`.
See the [tagged pypdf usage example](https://github.com/py-pdf/pypdf/blob/6.16.1/README.md#L42-L51).

The pypdf streaming example iterates through every item in `reader.pages`.
See the [tagged pypdf streaming example](https://github.com/py-pdf/pypdf/blob/6.16.1/docs/user/streaming-data.md#L48-L53).

The fpdf2 2.8.8 example creates an `FPDF` object and adds a page.
It selects a font, writes text, and writes `tuto1.pdf`.
See the [tagged fpdf2 example](https://github.com/py-pdf/fpdf2/blob/2.8.8/tutorial/tuto1.py#L1-L7).

The fpdf2 tutorial defines the roles of `add_page()`, `cell()`, and `output()`.
It states that `output(path)` saves the document at that path.
See the [tagged fpdf2 tutorial](https://github.com/py-pdf/fpdf2/blob/2.8.8/docs/Tutorial.md#L27-L67).

## Lower-bound evidence

pypdf 6.16.0 satisfies the `>=6.16` bound.
Its tagged example provides all required reading operations.
See the [pypdf 6.16.0 usage example](https://github.com/py-pdf/pypdf/blob/6.16.0/README.md#L42-L51).

pypdf 6.16.0 requires Python 3.9 or later.
Its classifiers include Python 3.12.
PyPI marks its release files as not yanked.
See the [pypdf 6.16.0 PyPI API](https://pypi.org/pypi/pypdf/6.16.0/json).

fpdf2 2.8.1 satisfies the `>=2.8` bound.
Its tagged example provides all required generation operations.
See the [fpdf2 2.8.1 example](https://github.com/py-pdf/fpdf2/blob/2.8.1/tutorial/tuto1.py#L1-L7).

fpdf2 2.8.1 requires Python 3.7 or later.
Its classifiers include Python 3.12.
PyPI marks its release files as not yanked.
See the [fpdf2 2.8.1 PyPI API](https://pypi.org/pypi/fpdf2/2.8.1/json).

## Release and Python evidence

PyPI reported pypdf 6.16.1 as the current release on the research date.
See the [current pypdf PyPI API](https://pypi.org/pypi/pypdf/json).

The release requires Python 3.9 or later.
Its classifiers include Python 3.12, 3.13, and 3.14.
PyPI marks both release files as not yanked.
See the [pypdf 6.16.1 PyPI API](https://pypi.org/pypi/pypdf/6.16.1/json).

PyPI reported fpdf2 2.8.8 as the current release on the research date.
See the [current fpdf2 PyPI API](https://pypi.org/pypi/fpdf2/json).

The release requires Python 3.10 or later.
Its classifiers include Python 3.12, 3.13, and 3.14.
PyPI marks both release files as not yanked.
See the [fpdf2 2.8.8 PyPI API](https://pypi.org/pypi/fpdf2/2.8.8/json).

Both releases use the `Development Status :: 5 - Production/Stable` classifier.
See the tagged [pypdf metadata](https://github.com/py-pdf/pypdf/blob/6.16.1/pyproject.toml#L14-L25).
See the tagged [fpdf2 metadata](https://github.com/py-pdf/fpdf2/blob/2.8.8/pyproject.toml#L10-L32).

Both releases support the repository's Python 3.12 minimum in [`pyproject.toml`](../../pyproject.toml).
Both explicitly classify Python 3.12 through 3.14 and set no upper Python bound.

## Package name note

Install the `fpdf2` distribution.
Import its public class with `from fpdf import FPDF`.
The [tagged fpdf2 example](https://github.com/py-pdf/fpdf2/blob/2.8.8/tutorial/tuto1.py#L1-L3) confirms this mapping.
