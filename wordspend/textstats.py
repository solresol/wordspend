"""Text length helpers for source-to-translation spend analysis."""

from __future__ import annotations

import re
import unicodedata

WORD_PATTERN = re.compile(r"(?u)\b\w+\b")
NONSPACE_PATTERN = re.compile(r"\S", re.UNICODE)

ENGLISH_VOWELS = "aeiouy"
GREEK_VOWELS = set("αεηιουωάέήίόύώϊϋΐΰΑΕΗΙΟΥΩΆΈΉΊΌΎΏΪΫ")
GREEK_DIPHTHONGS = {
    "αι",
    "ει",
    "οι",
    "υι",
    "αυ",
    "ευ",
    "ηυ",
    "ου",
    "ΑΙ",
    "ΕΙ",
    "ΟΙ",
    "ΥΙ",
    "ΑΥ",
    "ΕΥ",
    "ΗΥ",
    "ΟΥ",
}


def normalize_text(text: object) -> str:
    """Return NFC-normalized text with a stable string representation."""
    if text is None:
        return ""
    return unicodedata.normalize("NFC", str(text))


def tokenize(text: object) -> list[str]:
    """Return word-like tokens for alphabetic corpora."""
    return WORD_PATTERN.findall(normalize_text(text))


def count_tokens(text: object) -> int:
    """Count word-like tokens."""
    return len(tokenize(text))


def count_characters(text: object) -> int:
    """Count non-space, non-punctuation-ish word characters."""
    return sum(1 for token in tokenize(text) for _ in token)


def estimate_english_syllables(text: object) -> int:
    """Estimate English syllables with a simple vowel-group heuristic."""
    total = 0
    for token in tokenize(text):
        word = token.casefold()
        groups = 0
        in_group = False
        for char in word:
            is_vowel = char in ENGLISH_VOWELS
            if is_vowel and not in_group:
                groups += 1
            in_group = is_vowel
        if word.endswith("e") and groups > 1 and not word.endswith(("le", "ue")):
            groups -= 1
        total += max(groups, 1)
    return total


def estimate_greek_syllables(text: object) -> int:
    """Estimate Greek syllables by counting vowel nuclei and common diphthongs."""
    total = 0
    for token in tokenize(text):
        i = 0
        nuclei = 0
        while i < len(token):
            pair = token[i : i + 2]
            if pair in GREEK_DIPHTHONGS:
                nuclei += 1
                i += 2
                continue
            if token[i] in GREEK_VOWELS:
                nuclei += 1
            i += 1
        total += max(nuclei, 1) if token else 0
    return total


def estimate_syllables(text: object, language: str | None = None) -> int:
    """Estimate syllables for a known language, falling back to English-like."""
    language_key = (language or "").casefold()
    if "greek" in language_key:
        return estimate_greek_syllables(text)
    return estimate_english_syllables(text)


def length_metrics(source_text: object, target_text: object, source_language: str = "", target_language: str = "English") -> dict[str, int]:
    """Compute the basic length metrics stored for each aligned segment."""
    return {
        "source_token_count": count_tokens(source_text),
        "target_token_count": count_tokens(target_text),
        "source_char_count": count_characters(source_text),
        "target_char_count": count_characters(target_text),
        "source_syllable_count": estimate_syllables(source_text, source_language),
        "target_syllable_count": estimate_syllables(target_text, target_language),
    }
