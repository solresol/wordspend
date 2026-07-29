"""Deterministic book extraction for structurally aligned translations."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from .tokenization import tokenize_with_offsets, tokenizer_id_for_language


BOOK_HEADING_RE = re.compile(r"(?m)^BOOK ([IVXLCDM]+)\.\r?$")
PARAGRAPH_RE = re.compile(r"(?m)(?:^[^\r\n]+\r?\n?)+")
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


@dataclass(frozen=True)
class TranslationBook:
    """One extracted translation book and its location in the prepared text."""

    book: int
    start_char: int
    end_char: int
    start_line: int
    end_line: int
    text: str
    text_sha256: str
    token_count: int


def roman_to_int(value: str) -> int:
    """Parse a canonical positive Roman numeral."""
    if not value or any(character not in ROMAN_VALUES for character in value):
        raise ValueError(f"invalid Roman numeral {value!r}")

    total = 0
    previous = 0
    for character in reversed(value):
        current = ROMAN_VALUES[character]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current

    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remainder = total
    canonical = []
    for amount, numeral in numerals:
        while remainder >= amount:
            canonical.append(numeral)
            remainder -= amount
    if "".join(canonical) != value:
        raise ValueError(f"non-canonical Roman numeral {value!r}")
    return total


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def extract_translation_books(
    text: str,
    language_code: str,
    *,
    expected_book_count: int,
    leading_paragraphs_to_skip: int,
) -> list[TranslationBook]:
    """Extract book bodies after headings and declared leading paratext."""
    if not unicodedata.is_normalized("NFC", text):
        raise ValueError("Prepared translation text must be NFC-normalized.")
    if expected_book_count < 1:
        raise ValueError("expected_book_count must be positive")
    if leading_paragraphs_to_skip < 0:
        raise ValueError("leading_paragraphs_to_skip must not be negative")

    headings = list(BOOK_HEADING_RE.finditer(text))
    if len(headings) != expected_book_count:
        raise ValueError(
            f"expected {expected_book_count} BOOK headings, found {len(headings)}"
        )

    book_numbers = [roman_to_int(match.group(1)) for match in headings]
    expected_numbers = list(range(1, expected_book_count + 1))
    if book_numbers != expected_numbers:
        raise ValueError(
            f"BOOK headings must be consecutive 1..{expected_book_count}, got {book_numbers}"
        )

    tokenizer_id_for_language(language_code)
    books: list[TranslationBook] = []
    for index, heading in enumerate(headings):
        section_start = heading.end()
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[section_start:section_end]
        paragraphs = list(PARAGRAPH_RE.finditer(section))
        if len(paragraphs) <= leading_paragraphs_to_skip:
            raise ValueError(
                f"BOOK {heading.group(1)} has {len(paragraphs)} paragraph(s), "
                f"cannot skip {leading_paragraphs_to_skip}"
            )

        start_char = section_start + paragraphs[leading_paragraphs_to_skip].start()
        while start_char < section_end and text[start_char].isspace():
            start_char += 1
        end_char = section_end
        while end_char > start_char and text[end_char - 1].isspace():
            end_char -= 1

        body = text[start_char:end_char].replace("\r\n", "\n").replace("\r", "\n")
        body = unicodedata.normalize("NFC", body)
        if not body:
            raise ValueError(f"BOOK {heading.group(1)} has no translation body")
        tokens = tokenize_with_offsets(body, language_code)
        if not tokens:
            raise ValueError(f"BOOK {heading.group(1)} has no tokens")

        books.append(
            TranslationBook(
                book=book_numbers[index],
                start_char=start_char,
                end_char=end_char,
                start_line=_line_number(text, start_char),
                end_line=_line_number(text, end_char),
                text=body,
                text_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                token_count=len(tokens),
            )
        )
    return books
