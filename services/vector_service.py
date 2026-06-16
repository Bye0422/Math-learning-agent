import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SEPARATORS,
    VECTOR_COLLECTION_PREFIX,
)
from services.llm_service import get_embeddings


def split_documents(documents):
    """
    将 Document 切成 chunk。
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=CHUNK_SEPARATORS,
    )

    chunks = text_splitter.split_documents(documents)

    clean_chunks = []

    for idx, chunk in enumerate(chunks, start=1):
        if chunk.page_content and chunk.page_content.strip():
            chunk.page_content = chunk.page_content.strip()
            chunk.metadata["chunk_id"] = idx
            clean_chunks.append(chunk)

    return clean_chunks


def create_vector_db(chunks):
    """
    创建 Chroma 向量库。
    """
    embeddings = get_embeddings()

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