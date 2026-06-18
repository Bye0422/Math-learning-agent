import re
from copy import deepcopy

from langchain_core.documents import Document


QUESTION_MARKER_PATTERN = re.compile(
    r"(?m)(?P<marker>"
    r"(?:^|\n)\s*(?:第\s*[\(（]?\d+[\)）]?\s*(?:题|小题|问))|"
    r"(?:^|\n)\s*(?:第\s*[\(（]?[一二两三四五六七八九十]+[\)）]?\s*(?:题|小题|问))|"
    r"(?:^|\n)\s*(?:\d+\s*[\.．、])|"
    r"(?:^|\n)\s*(?:[一二两三四五六七八九十]+\s*[、\.．])|"
    r"(?:^|\n)\s*(?:[①②③④⑤⑥⑦⑧⑨⑩])"
    r")"
)


def find_question_markers(text):
    if not text:
        return []

    return [
        {
            "start": match.start("marker"),
            "end": match.end("marker"),
            "marker": match.group("marker").strip(),
        }
        for match in QUESTION_MARKER_PATTERN.finditer(text)
    ]


def split_text_by_question_markers(text, min_markers=2):
    markers = find_question_markers(text)

    if len(markers) < min_markers:
        return []

    blocks = []
    leading_text = text[:markers[0]["start"]].strip()

    if leading_text:
        blocks.append(
            {
                "content": leading_text,
                "marker": "",
                "question_index": 0,
            }
        )

    for index, marker in enumerate(markers):
        start = marker["start"]
        end = markers[index + 1]["start"] if index + 1 < len(markers) else len(text)
        content = text[start:end].strip()

        if not content:
            continue

        blocks.append(
            {
                "content": content,
                "marker": marker["marker"],
                "question_index": index + 1,
            }
        )

    return blocks


def split_documents_by_questions(documents, min_markers=2):
    question_docs = []

    for doc in documents:
        blocks = split_text_by_question_markers(
            doc.page_content or "",
            min_markers=min_markers,
        )

        if not blocks:
            question_docs.append(doc)
            continue

        for block in blocks:
            metadata = deepcopy(doc.metadata or {})
            metadata["question_chunk"] = True
            metadata["question_marker"] = block["marker"]
            metadata["question_index"] = block["question_index"]

            if block["question_index"]:
                metadata["location"] = (
                    f"{metadata.get('location', '全文')} | 题块 {block['question_index']}"
                )

            question_docs.append(
                Document(
                    page_content=block["content"],
                    metadata=metadata,
                )
            )

    return question_docs
