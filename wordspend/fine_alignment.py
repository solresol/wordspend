"""Deterministic candidate units for human-reviewed fine alignment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .tokenization import tokenize_with_offsets


PROPOSAL_METHOD = "proportional_translation_paragraph_tokens_v1"
PARAGRAPH_RE = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class TargetParagraph:
    """One non-empty translation paragraph with book-local locations."""

    paragraph: int
    start_char: int
    end_char: int
    start_token: int
    end_token: int
    token_count: int
    text: str


@dataclass(frozen=True)
class AlignmentCandidate:
    """One automatically proposed source-line range and target paragraph pair."""

    segment: int
    source_start_index: int
    source_end_index: int
    target: TargetParagraph


def extract_target_paragraphs(text: str, language_code: str) -> list[TargetParagraph]:
    """Return ordered translation paragraphs and their whole-book token spans."""
    tokens = tokenize_with_offsets(text, language_code)
    paragraphs: list[TargetParagraph] = []
    token_cursor = 0

    for match in PARAGRAPH_RE.finditer(text):
        while token_cursor < len(tokens) and tokens[token_cursor].end_char <= match.start():
            token_cursor += 1
        first_token = token_cursor
        while token_cursor < len(tokens) and tokens[token_cursor].start_char < match.end():
            token_cursor += 1
        if first_token == token_cursor:
            continue
        paragraph_tokens = tokens[first_token:token_cursor]
        paragraphs.append(
            TargetParagraph(
                paragraph=len(paragraphs) + 1,
                start_char=match.start(),
                end_char=match.end(),
                start_token=paragraph_tokens[0].token_index,
                end_token=paragraph_tokens[-1].token_index,
                token_count=len(paragraph_tokens),
                text=match.group(0),
            )
        )

    if not paragraphs:
        raise ValueError("Translation book has no non-empty paragraphs")
    return paragraphs


def propose_source_ranges(
    source_lines: Sequence[object], target_paragraphs: Sequence[TargetParagraph]
) -> list[AlignmentCandidate]:
    """Allocate contiguous source lines in proportion to target paragraph tokens.

    This is a review-queue proposal only. It does not claim semantic alignment.
    Every source line is allocated exactly once and every target paragraph receives
    at least one source line, so reviewers can adjust explicit neighbouring ranges.
    """
    if not source_lines:
        raise ValueError("Source book has no lines")
    if not target_paragraphs:
        raise ValueError("Translation book has no paragraphs")
    if len(source_lines) < len(target_paragraphs):
        raise ValueError("Source book has fewer lines than translation paragraphs")

    total_tokens = sum(paragraph.token_count for paragraph in target_paragraphs)
    if total_tokens < 1:
        raise ValueError("Translation paragraphs have no tokens")

    candidates: list[AlignmentCandidate] = []
    source_start = 0
    cumulative_tokens = 0
    source_count = len(source_lines)
    paragraph_count = len(target_paragraphs)

    for index, paragraph in enumerate(target_paragraphs, start=1):
        cumulative_tokens += paragraph.token_count
        if index == paragraph_count:
            source_end = source_count
        else:
            proposed_end = round(cumulative_tokens * source_count / total_tokens)
            minimum_end = source_start + 1
            maximum_end = source_count - (paragraph_count - index)
            source_end = min(max(proposed_end, minimum_end), maximum_end)
        candidates.append(
            AlignmentCandidate(
                segment=index,
                source_start_index=source_start,
                source_end_index=source_end,
                target=paragraph,
            )
        )
        source_start = source_end

    return candidates
