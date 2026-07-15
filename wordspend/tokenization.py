"""Deterministic tokenization for prepared paper-facing texts."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass


TOKENIZER_ID = "unicode-alphabetic-apostrophe-v1"
SPACE_DELIMITED_ALPHABETIC_LANGUAGES = frozenset(
    {
        "ang",  # Old English
        "de",
        "en",
        "fr",
        "grc",  # Ancient Greek
        "it",
        "la",
        "sa",  # Sanskrit in alphabetic transcription
    }
)
APOSTROPHES = frozenset({"'", "\N{RIGHT SINGLE QUOTATION MARK}"})


@dataclass(frozen=True)
class TokenSpan:
    """One token and its location in the decoded prepared text."""

    token_index: int
    token: str
    normalized_token: str
    start_char: int
    end_char: int
    line_number: int


def base_language_code(language_code: object) -> str:
    """Return the lower-case base of a BCP-47-like language code."""
    return str(language_code or "").strip().lower().split("-", 1)[0]


def tokenizer_id_for_language(language_code: object) -> str:
    """Return the explicit tokenizer ID, rejecting unsupported language families."""
    code = base_language_code(language_code)
    if code not in SPACE_DELIMITED_ALPHABETIC_LANGUAGES:
        raise ValueError(
            f"No paper-facing tokenizer is configured for language code {language_code!r}; "
            "add an explicit language-specific tokenizer before using this text."
        )
    return TOKENIZER_ID


def is_letter(character: str) -> bool:
    """Return whether a character is a Unicode letter."""
    return unicodedata.category(character).startswith("L")


def is_letter_or_mark(character: str) -> bool:
    """Return whether a character continues an alphabetic Unicode token."""
    return unicodedata.category(character)[0] in {"L", "M"}


def iter_token_offsets(value: str) -> Iterator[tuple[int, int]]:
    """Yield token character offsets without dropping combining marks."""
    index = 0
    while index < len(value):
        if not is_letter(value[index]):
            index += 1
            continue

        start = index
        index += 1
        while index < len(value):
            if is_letter_or_mark(value[index]):
                index += 1
                continue
            if (
                value[index] in APOSTROPHES
                and index + 1 < len(value)
                and is_letter(value[index + 1])
            ):
                index += 1
                continue
            break
        yield start, index


def tokenize_with_offsets(text: object, language_code: object) -> list[TokenSpan]:
    """Tokenize text and retain deterministic character and line locations."""
    tokenizer_id_for_language(language_code)
    value = "" if text is None else str(text)
    if not unicodedata.is_normalized("NFC", value):
        raise ValueError("Prepared text must be NFC-normalized before paper-facing tokenization.")
    spans: list[TokenSpan] = []
    line_number = 1
    scanned_to = 0

    for token_index, (start, end) in enumerate(iter_token_offsets(value), start=1):
        line_number += value.count("\n", scanned_to, start)
        token = value[start:end]
        spans.append(
            TokenSpan(
                token_index=token_index,
                token=token,
                normalized_token=unicodedata.normalize("NFC", token.casefold()),
                start_char=start,
                end_char=end,
                line_number=line_number,
            )
        )
        scanned_to = end

    return spans
