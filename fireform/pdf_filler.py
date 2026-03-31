from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pypdf import PdfReader, PdfWriter


class PdfFillError(RuntimeError):
    pass


def inspect_pdf_fields(template_path: str) -> list[str]:
    template = Path(template_path)
    if not template.exists():
        raise PdfFillError(f"Template not found: {template}")

    reader = PdfReader(str(template))
    fields = reader.get_fields() or {}
    return sorted(fields.keys())


def fill_pdf(
    template_path: str,
    field_values: Mapping[
        str,
        str | list[str] | tuple[str, str, float],
    ],
    output_path: str,
) -> Path:
    template = Path(template_path)
    if not template.exists():
        raise PdfFillError(f"Template not found: {template}")

    reader = PdfReader(str(template))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    if not writer.pages:
        raise PdfFillError(f"Template has no pages: {template}")

    writer.update_page_form_field_values(
        writer.pages[0],
        dict(field_values),
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file_obj:
        writer.write(file_obj)

    return output
