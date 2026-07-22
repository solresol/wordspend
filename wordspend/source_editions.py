"""Validation and TEI preparation for paper-facing source editions."""

from __future__ import annotations

import csv
import datetime as dt
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_COLUMNS = [
    "source_edition_id",
    "work_id",
    "work_title",
    "source_language",
    "source_language_code",
    "author",
    "editors",
    "edition_title",
    "edition_label",
    "publication_date",
    "publication_date_text",
    "publisher",
    "publication_place",
    "digital_provider",
    "canonical_id",
    "version_id",
    "catalog_url",
    "download_url",
    "download_format",
    "rights_status",
    "rights_basis",
    "rights_url",
    "editorial_status",
    "paper_facing_eligible",
]

PAPER_RIGHTS_ALLOWED = {
    "public_domain_us",
    "public_domain_worldwide",
    "open_license",
}

ALLOWED_EDITORIAL_STATUS = {
    "human_edited_published",
    "machine_bootstrap",
    "mixed_or_unclear",
}

LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"


@dataclass(frozen=True)
class SourceLine:
    """One source-edition line with its stable work-local reference."""

    reference: str
    book: int
    line: int
    text: str
    line_status: str


def is_yes(value: object) -> bool:
    return str(value).strip().lower() == "yes"


def _validate_url(value: str, field: str, label: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{label}: {field} must be an http(s) URL, got {value!r}")


def validate_source_edition_registry(path: Path) -> tuple[int, int, list[str]]:
    """Validate source-edition provenance and paper-facing eligibility."""

    if not path.exists():
        return 0, 0, [f"{path}: file does not exist"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    paper_facing_count = 0

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            return 0, 0, [f"{path}: missing required columns: {', '.join(missing)}"]

        row_count = 0
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            edition_id = (row.get("source_edition_id") or "").strip()
            label = edition_id or f"row {row_number}"

            for column in REQUIRED_COLUMNS:
                if not (row.get(column) or "").strip():
                    errors.append(f"{label}: {column} is required")

            if edition_id in seen_ids:
                errors.append(f"{label}: duplicate source_edition_id")
            seen_ids.add(edition_id)

            for slug_field in ("source_edition_id", "work_id"):
                value = (row.get(slug_field) or "").strip()
                if value and not SLUG_RE.fullmatch(value):
                    errors.append(f"{label}: {slug_field} must be a lowercase slug")

            language_code = (row.get("source_language_code") or "").strip()
            if language_code and not LANGUAGE_CODE_RE.fullmatch(language_code):
                errors.append(f"{label}: source_language_code has invalid language code {language_code!r}")

            publication_date = (row.get("publication_date") or "").strip()
            if publication_date and not re.fullmatch(r"\d{4}", publication_date):
                try:
                    dt.date.fromisoformat(publication_date)
                except ValueError:
                    errors.append(
                        f"{label}: publication_date must be a year or ISO date, got {publication_date!r}"
                    )

            for url_field in ("catalog_url", "download_url", "rights_url"):
                value = (row.get(url_field) or "").strip()
                if value:
                    _validate_url(value, url_field, label, errors)

            editorial_status = (row.get("editorial_status") or "").strip()
            if editorial_status and editorial_status not in ALLOWED_EDITORIAL_STATUS:
                errors.append(
                    f"{label}: editorial_status must be one of "
                    f"{', '.join(sorted(ALLOWED_EDITORIAL_STATUS))}"
                )

            eligible = (row.get("paper_facing_eligible") or "").strip().lower()
            if eligible not in {"yes", "no"}:
                errors.append(f"{label}: paper_facing_eligible must be yes or no")

            if is_yes(row.get("paper_facing_eligible") or ""):
                paper_facing_count += 1
                rights_status = (row.get("rights_status") or "").strip()
                if rights_status not in PAPER_RIGHTS_ALLOWED:
                    errors.append(
                        f"{label}: paper-facing source editions need an allowed rights_status, "
                        f"got {rights_status!r}"
                    )
                if editorial_status != "human_edited_published":
                    errors.append(
                        f"{label}: paper-facing source editions must be human_edited_published"
                    )

    return row_count, paper_facing_count, errors


def extract_tei_source_lines(payload: bytes, expected_urn: str) -> list[SourceLine]:
    """Extract ordered book/line records from one CTS-addressable TEI edition."""

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError(f"invalid TEI XML: {error}") from error

    ns = {"tei": TEI_NAMESPACE}
    edition = root.find(".//tei:div[@type='edition']", ns)
    if edition is None:
        raise ValueError("TEI source has no edition div")
    if (edition.get("n") or "").strip() != expected_urn:
        raise ValueError(
            f"TEI edition URN does not match registry: expected {expected_urn!r}, "
            f"got {(edition.get('n') or '').strip()!r}"
        )

    records: list[SourceLine] = []
    seen_references: set[str] = set()
    previous_book = 0
    for book_element in edition.findall("./tei:div[@type='textpart']", ns):
        book_value = (book_element.get("n") or "").strip()
        if not book_value.isdigit() or int(book_value) < 1:
            raise ValueError(f"TEI book number must be a positive integer, got {book_value!r}")
        book = int(book_value)
        if book <= previous_book:
            raise ValueError("TEI books must be in strictly increasing order")
        previous_book = book

        previous_line = 0
        for line_element in book_element.findall(".//tei:l", ns):
            line_value = (line_element.get("n") or "").strip()
            if not line_value.isdigit() or int(line_value) < 1:
                raise ValueError(
                    f"TEI line number in book {book} must be a positive integer, got {line_value!r}"
                )
            line = int(line_value)
            if line <= previous_line:
                raise ValueError(f"TEI lines in book {book} must be in strictly increasing order")
            previous_line = line

            reference = f"{book}.{line}"
            if reference in seen_references:
                raise ValueError(f"duplicate TEI source reference {reference}")
            seen_references.add(reference)

            text = " ".join("".join(line_element.itertext()).split())
            text = unicodedata.normalize("NFC", text)
            if not text:
                raise ValueError(f"TEI source reference {reference} has no text")
            line_status = (
                "editorially_deleted"
                if line_element.find(".//tei:del", ns) is not None
                else "edition_text"
            )
            records.append(
                SourceLine(
                    reference=reference,
                    book=book,
                    line=line,
                    text=text,
                    line_status=line_status,
                )
            )

    if not records:
        raise ValueError("TEI edition contains no source lines")
    return records
