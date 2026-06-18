import re


DEFAULT_PREVIEW_LENGTH = 160


def _as_text(value):
    if value is None:
        return ""
    return str(value)


def _compact_whitespace(text):
    return re.sub(r"\s+", " ", _as_text(text)).strip()


def _build_preview(text, max_length=DEFAULT_PREVIEW_LENGTH):
    preview = _compact_whitespace(text)

    if max_length is None or max_length <= 0:
        return preview

    if len(preview) <= max_length:
        return preview

    return preview[: max_length - 1].rstrip() + "…"


def build_chunk_debug_rows(chunks, preview_length=DEFAULT_PREVIEW_LENGTH):
    rows = []

    for index, chunk in enumerate(chunks or [], start=1):
        metadata = getattr(chunk, "metadata", None) or {}
        page_content = getattr(chunk, "page_content", "") or ""

        rows.append(
            {
                "chunk_id": metadata.get("chunk_id", index),
                "source": _as_text(metadata.get("source", "")),
                "location": _as_text(metadata.get("location", "")),
                "file_type": _as_text(metadata.get("file_type", "")),
                "question_chunk": bool(metadata.get("question_chunk", False)),
                "question_marker": _as_text(metadata.get("question_marker", "")),
                "question_index": metadata.get("question_index", ""),
                "char_count": len(page_content),
                "quality_level": _as_text(metadata.get("chunk_quality_level", "")),
                "quality_issues": "；".join(metadata.get("chunk_quality_issues", []) or []),
                "option_count": metadata.get("chunk_option_count", ""),
                "question_marker_count": metadata.get("chunk_question_marker_count", ""),
                "exam_text_cleaned": bool(metadata.get("exam_text_cleaned", False)),
                "chunk_corrected": bool(metadata.get("chunk_corrected", False)),
                "preview": _build_preview(page_content, preview_length),
            }
        )

    return rows


def filter_chunk_debug_rows(rows, keyword="", question_marker=""):
    keyword_text = _compact_whitespace(keyword).casefold()
    marker_text = _compact_whitespace(question_marker).casefold()

    filtered_rows = []

    for row in rows or []:
        if keyword_text and not _row_matches_keyword(row, keyword_text):
            continue

        if marker_text and not _row_matches_question_marker(row, marker_text):
            continue

        filtered_rows.append(row)

    return filtered_rows


def _row_matches_keyword(row, keyword_text):
    searchable_fields = (
        row.get("preview", ""),
        row.get("source", ""),
        row.get("location", ""),
        row.get("question_marker", ""),
        row.get("quality_level", ""),
        row.get("quality_issues", ""),
    )

    return any(keyword_text in _compact_whitespace(value).casefold() for value in searchable_fields)


def _row_matches_question_marker(row, marker_text):
    row_marker = _compact_whitespace(row.get("question_marker", "")).casefold()

    if not row_marker:
        return False

    return row_marker == marker_text or marker_text in row_marker
