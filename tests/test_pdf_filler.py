from __future__ import annotations

from pathlib import Path

from fireform.pdf_filler import fill_pdf, inspect_pdf_fields


class DummyWriter:
    def __init__(self):
        self.pages = []
        self.updated = None

    def add_page(self, page):
        self.pages.append(page)

    def update_page_form_field_values(self, page, values):
        self.updated = values

    def write(self, file_obj):
        file_obj.write(b"pdf")


class DummyReader:
    def __init__(self, *_args, **_kwargs):
        self.pages = [object()]

    def get_fields(self):
        return {"incident_id": {}, "incident_date": {}}


def test_fill_pdf_writes_output(tmp_path, mocker):
    template = tmp_path / "template.pdf"
    template.write_bytes(b"dummy")

    mocker.patch("fireform.pdf_filler.PdfReader", DummyReader)
    mocker.patch("fireform.pdf_filler.PdfWriter", DummyWriter)

    output = tmp_path / "output.pdf"
    result = fill_pdf(str(template), {"incident_id": "FF-1"}, str(output))

    assert isinstance(result, Path)
    assert result.exists()


def test_inspect_pdf_fields_returns_sorted_names(tmp_path, mocker):
    template = tmp_path / "template.pdf"
    template.write_bytes(b"dummy")

    mocker.patch("fireform.pdf_filler.PdfReader", DummyReader)

    fields = inspect_pdf_fields(str(template))
    assert fields == ["incident_date", "incident_id"]
