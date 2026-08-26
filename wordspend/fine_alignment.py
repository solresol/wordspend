"""Deterministic candidate units for human-reviewed fine alignment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .tokenization import tokenize_with_offsets


PROPOSAL_METHOD = "proportional_translation_paragraph_tokens_v1"
PARAGRAPH_RE = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.DOTALL)
HUMAN_REVIEW_COLUMNS = (
    "review_decision",
    "reviewed_source_start_ref",
    "reviewed_source_end_ref",
    "reviewer",
    "reviewed_at",
    "review_notes",
)
REVIEW_DECISIONS = frozenset({"accept_proposed_range", "adjust_source_range"})


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


def prepare_review_worklist_rows(
    candidate_rows: Sequence[Mapping[str, object]], candidate_sha256: str
) -> list[dict[str, object]]:
    """Create pending human-review rows without promoting candidate evidence."""
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256):
        raise ValueError("Candidate SHA-256 must be 64 lowercase hexadecimal characters")
    if not candidate_rows:
        raise ValueError("Candidate file has no rows")

    required = {
        "candidate_id",
        "work_id",
        "source_edition_id",
        "translation_source_id",
        "book",
        "segment_index",
        "source_start_ref",
        "source_end_ref",
        "source_line_count",
        "target_paragraph",
        "source_text",
        "target_text",
        "proposal_status",
        "review_status",
        "paper_facing_eligible",
        "analysis_status",
    }
    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for expected_segment, candidate in enumerate(candidate_rows, start=1):
        missing = sorted(required - candidate.keys())
        if missing:
            raise ValueError(f"Candidate row is missing fields: {', '.join(missing)}")
        candidate_id = str(candidate["candidate_id"])
        if not candidate_id or candidate_id in seen_ids:
            raise ValueError(f"Candidate IDs must be non-empty and unique: {candidate_id!r}")
        seen_ids.add(candidate_id)
        if int(candidate["segment_index"]) != expected_segment:
            raise ValueError("Candidate segment indexes must be consecutive from 1")
        if (
            candidate["proposal_status"] != "machine_proposed_unreviewed"
            or candidate["review_status"] != "pending_human_review"
            or candidate["paper_facing_eligible"] != "no"
            or candidate["analysis_status"] != "excluded_until_human_review"
        ):
            raise ValueError(
                f"{candidate_id}: candidate must remain unreviewed and analysis-excluded"
            )

        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_file_sha256": candidate_sha256,
                "work_id": candidate["work_id"],
                "source_edition_id": candidate["source_edition_id"],
                "translation_source_id": candidate["translation_source_id"],
                "book": candidate["book"],
                "segment_index": candidate["segment_index"],
                "target_paragraph": candidate["target_paragraph"],
                "proposed_source_start_ref": candidate["source_start_ref"],
                "proposed_source_end_ref": candidate["source_end_ref"],
                "proposed_source_line_count": candidate["source_line_count"],
                "review_decision": "",
                "reviewed_source_start_ref": "",
                "reviewed_source_end_ref": "",
                "reviewer": "",
                "reviewed_at": "",
                "review_notes": "",
                "source_text": candidate["source_text"],
                "target_text": candidate["target_text"],
                "review_status": "pending_human_review",
                "paper_facing_eligible": "no",
                "analysis_status": "excluded_until_completed_review",
            }
        )
    return rows


def review_worklist_has_human_input(rows: Sequence[Mapping[str, object]]) -> bool:
    """Return whether regenerating a worklist would erase entered review data."""
    return any(
        str(row.get(column, "")).strip()
        for row in rows
        for column in HUMAN_REVIEW_COLUMNS
    )


def import_completed_review_rows(
    worklist_rows: Sequence[Mapping[str, object]],
    candidate_rows: Sequence[Mapping[str, object]],
    source_lines: Sequence[Mapping[str, object]],
    candidate_sha256: str,
) -> list[dict[str, object]]:
    """Validate completed review decisions and normalize them for adjudication.

    A completed review is not promoted to paper-facing evidence here. The returned
    rows remain excluded until a separate adjudication stage approves them.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256):
        raise ValueError("Candidate SHA-256 must be 64 lowercase hexadecimal characters")
    if not worklist_rows or len(worklist_rows) != len(candidate_rows):
        raise ValueError("Worklist and candidate rows must have the same non-zero length")
    if not source_lines:
        raise ValueError("Source edition book has no lines")

    source_by_ref: dict[str, tuple[int, Mapping[str, object]]] = {}
    for position, line in enumerate(source_lines):
        reference = str(line.get("reference", "")).strip()
        if not reference or reference in source_by_ref:
            raise ValueError(f"Source references must be non-empty and unique: {reference!r}")
        source_by_ref[reference] = (position, line)

    immutable_pairs = {
        "candidate_id": "candidate_id",
        "work_id": "work_id",
        "source_edition_id": "source_edition_id",
        "translation_source_id": "translation_source_id",
        "book": "book",
        "segment_index": "segment_index",
        "target_paragraph": "target_paragraph",
        "proposed_source_start_ref": "source_start_ref",
        "proposed_source_end_ref": "source_end_ref",
        "proposed_source_line_count": "source_line_count",
        "source_text": "source_text",
        "target_text": "target_text",
    }
    imported: list[dict[str, object]] = []
    previous_end = -1

    for expected_segment, (worklist, candidate) in enumerate(
        zip(worklist_rows, candidate_rows), start=1
    ):
        candidate_id = str(candidate.get("candidate_id", "")).strip()
        if int(candidate.get("segment_index", 0)) != expected_segment:
            raise ValueError("Candidate segment indexes must be consecutive from 1")
        if str(worklist.get("candidate_file_sha256", "")) != candidate_sha256:
            raise ValueError(f"{candidate_id}: worklist candidate checksum does not match")
        for worklist_field, candidate_field in immutable_pairs.items():
            if str(worklist.get(worklist_field, "")) != str(
                candidate.get(candidate_field, "")
            ):
                raise ValueError(f"{candidate_id}: worklist field {worklist_field} changed")
        if (
            candidate.get("proposal_status") != "machine_proposed_unreviewed"
            or candidate.get("review_status") != "pending_human_review"
            or candidate.get("paper_facing_eligible") != "no"
            or candidate.get("analysis_status") != "excluded_until_human_review"
        ):
            raise ValueError(f"{candidate_id}: candidate is not pending and excluded")
        if (
            worklist.get("review_status") != "pending_human_review"
            or worklist.get("paper_facing_eligible") != "no"
            or worklist.get("analysis_status") != "excluded_until_completed_review"
        ):
            raise ValueError(f"{candidate_id}: worklist eligibility fields changed")

        decision = str(worklist.get("review_decision", "")).strip()
        if decision not in REVIEW_DECISIONS:
            allowed = ", ".join(sorted(REVIEW_DECISIONS))
            raise ValueError(f"{candidate_id}: review_decision must be one of {allowed}")
        reviewer = str(worklist.get("reviewer", "")).strip()
        if not reviewer:
            raise ValueError(f"{candidate_id}: reviewer is required")
        reviewed_at = str(worklist.get("reviewed_at", "")).strip()
        try:
            parsed_reviewed_at = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{candidate_id}: reviewed_at must be ISO 8601") from error
        if parsed_reviewed_at.tzinfo is None:
            raise ValueError(f"{candidate_id}: reviewed_at must include a timezone")

        proposed_start = str(candidate["source_start_ref"])
        proposed_end = str(candidate["source_end_ref"])
        entered_start = str(worklist.get("reviewed_source_start_ref", "")).strip()
        entered_end = str(worklist.get("reviewed_source_end_ref", "")).strip()
        if decision == "accept_proposed_range":
            if (entered_start or entered_end) and (
                entered_start != proposed_start or entered_end != proposed_end
            ):
                raise ValueError(
                    f"{candidate_id}: accepted range must be blank or match the proposal"
                )
            reviewed_start, reviewed_end = proposed_start, proposed_end
        else:
            if not entered_start or not entered_end:
                raise ValueError(f"{candidate_id}: adjusted range requires both references")
            if not str(worklist.get("review_notes", "")).strip():
                raise ValueError(f"{candidate_id}: adjusted range requires review_notes")
            reviewed_start, reviewed_end = entered_start, entered_end

        if reviewed_start not in source_by_ref or reviewed_end not in source_by_ref:
            raise ValueError(f"{candidate_id}: reviewed range is outside the source book")
        start_position = source_by_ref[reviewed_start][0]
        end_position = source_by_ref[reviewed_end][0]
        if start_position > end_position:
            raise ValueError(f"{candidate_id}: reviewed source range is reversed")
        if start_position != previous_end + 1:
            raise ValueError(
                f"{candidate_id}: reviewed ranges must be ordered with no gaps or overlaps"
            )
        previous_end = end_position
        selected_lines = source_lines[start_position : end_position + 1]

        imported.append(
            {
                "alignment_id": candidate_id,
                "work_id": candidate["work_id"],
                "source_edition_id": candidate["source_edition_id"],
                "translation_source_id": candidate["translation_source_id"],
                "book": candidate["book"],
                "segment_index": candidate["segment_index"],
                "alignment_level": "reviewed_source_line_range_to_translation_paragraph",
                "source_start_ref": reviewed_start,
                "source_end_ref": reviewed_end,
                "source_line_count": len(selected_lines),
                "source_editorially_deleted_line_count": sum(
                    line.get("line_status") == "editorially_deleted"
                    for line in selected_lines
                ),
                "target_paragraph": candidate["target_paragraph"],
                "target_start_token": candidate["target_start_token"],
                "target_end_token": candidate["target_end_token"],
                "target_token_count": candidate["target_token_count"],
                "target_start_char": candidate["target_start_char"],
                "target_end_char": candidate["target_end_char"],
                "source_text": "\n".join(str(line["text"]) for line in selected_lines),
                "target_text": candidate["target_text"],
                "source_prepared_sha256": candidate["source_prepared_sha256"],
                "target_book_text_sha256": candidate["target_book_text_sha256"],
                "translation_prepared_sha256": candidate[
                    "translation_prepared_sha256"
                ],
                "candidate_file_sha256": candidate_sha256,
                "review_decision": decision,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "review_notes": str(worklist.get("review_notes", "")).strip(),
                "review_status": "completed_human_review_pending_adjudication",
                "paper_facing_eligible": "no",
                "analysis_status": "excluded_until_adjudication",
            }
        )

    if previous_end != len(source_lines) - 1:
        raise ValueError("Reviewed ranges do not cover the end of the source book")
    return imported


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
