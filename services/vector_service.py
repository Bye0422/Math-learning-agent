import hashlib
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SEPARATORS,
    VECTOR_COLLECTION_PREFIX,
    ENABLE_QUESTION_CHUNKING,
    QUESTION_CHUNK_MIN_MARKERS,
    QUESTION_CHUNK_MAX_CHARS,
    ENABLE_VECTOR_CACHE,
    VECTOR_CACHE_DIR_NAME,
)
from services.llm_service import get_embeddings
from services.chunk_quality_service import inspect_chunk_quality
from services.correction_store_service import apply_chunk_corrections
from services.exam_text_cleaner import normalize_exam_text
from services.question_chunker import split_documents_by_questions


def normalize_documents_for_chunking(documents):
    normalized_documents = []

    for doc in documents or []:
        original_text = doc.page_content or ""
        normalized_text = normalize_exam_text(original_text)

        if normalized_text == original_text:
            normalized_documents.append(doc)
            continue

        metadata = dict(doc.metadata or {})
        metadata["exam_text_cleaned"] = True

        doc.page_content = normalized_text
        doc.metadata = metadata
        normalized_documents.append(doc)

    return normalized_documents


def split_documents(documents):
    """
    将 Document 切成 chunk。
    """
    source_documents = normalize_documents_for_chunking(documents)

    if ENABLE_QUESTION_CHUNKING:
        source_documents = split_documents_by_questions(
            documents,
            min_markers=QUESTION_CHUNK_MIN_MARKERS,
        )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=CHUNK_SEPARATORS,
    )

    chunks = []

    for doc in source_documents:
        content = (doc.page_content or "").strip()
        metadata = doc.metadata or {}

        if (
            metadata.get("question_chunk")
            and content
            and len(content) <= QUESTION_CHUNK_MAX_CHARS
        ):
            doc.page_content = content
            chunks.append(doc)
            continue

        chunks.extend(text_splitter.split_documents([doc]))

    clean_chunks = []

    for idx, chunk in enumerate(chunks, start=1):
        if chunk.page_content and chunk.page_content.strip():
            chunk.page_content = chunk.page_content.strip()
            chunk.metadata["chunk_id"] = idx
            chunk.metadata.update(inspect_chunk_quality(chunk))
            clean_chunks.append(chunk)

    return apply_chunk_corrections(clean_chunks)


def build_chunks_hash(chunks):
    hasher = hashlib.sha256()

    for chunk in chunks:
        metadata = chunk.metadata or {}
        hasher.update((chunk.page_content or "").encode("utf-8"))
        hasher.update(str(metadata.get("source", "")).encode("utf-8"))
        hasher.update(str(metadata.get("location", "")).encode("utf-8"))
        hasher.update(str(metadata.get("chunk_id", "")).encode("utf-8"))

    return hasher.hexdigest()[:16]


def create_vector_db(chunks):
    """
    创建 Chroma 向量库。
    """
    embeddings = get_embeddings()

    if ENABLE_VECTOR_CACHE:
        cache_key = build_chunks_hash(chunks)
        persist_dir = Path(VECTOR_CACHE_DIR_NAME) / cache_key
        collection_name = f"{VECTOR_COLLECTION_PREFIX}_{cache_key}"

        if (persist_dir / "chroma.sqlite3").exists():
            return Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(persist_dir),
            )

        persist_dir.mkdir(parents=True, exist_ok=True)

        return Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(persist_dir),
        )

    collection_name = f"{VECTOR_COLLECTION_PREFIX}_{uuid.uuid4().hex[:8]}"

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
    )

    return vector_db


def search_similar_chunks_with_score(vector_db, question, k):
    """
    返回带距离分数的检索结果。
    """
    return vector_db.similarity_search_with_score(question, k=k)
