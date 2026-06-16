import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config import MEMORY_DB_PATH, MEMORY_HISTORY_LIMIT


def now_text():
    """
    当前时间字符串。
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_dumps(data):
    """
    安全转换 JSON 字符串。
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return json.dumps(str(data), ensure_ascii=False)


def json_loads(text, default=None):
    """
    安全读取 JSON 字符串。
    """
    if default is None:
        default = {}

    if not text:
        return default

    try:
        return json.loads(text)
    except Exception:
        return default


def get_memory_db_path():
    """
    获取 memory.db 路径，并确保父目录存在。
    """
    db_path = Path(MEMORY_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection():
    """
    获取 SQLite 连接。
    """
    db_path = get_memory_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db():
    """
    初始化 Memory 数据库。
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                file_key TEXT,
                file_names TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                file_key TEXT,
                file_names TEXT,
                task_type TEXT,
                need_rag TEXT,
                answer_format TEXT,
                route TEXT,
                retrieval_question TEXT,
                top_k TEXT,
                candidate_top_n TEXT,
                rerank_used TEXT,
                retrieved_sources TEXT,
                validation_result TEXT,
                was_repaired INTEGER,
                elapsed_seconds REAL,
                error TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_created_at
            ON messages(created_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qa_turns_session_id
            ON qa_turns(session_id)
            """
        )

        conn.commit()

    finally:
        conn.close()


def ensure_session(session_id, file_key="", file_names=None):
    """
    确保 session 存在。
    """
    if file_names is None:
        file_names = []

    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()
        current_time = now_text()

        cursor.execute(
            """
            INSERT OR IGNORE INTO sessions (
                session_id,
                file_key,
                file_names,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                file_key,
                json_dumps(file_names),
                current_time,
                current_time,
            ),
        )

        cursor.execute(
            """
            UPDATE sessions
            SET file_key = ?,
                file_names = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                file_key,
                json_dumps(file_names),
                current_time,
                session_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def save_message(session_id, role, content, metadata=None):
    """
    保存单条消息。
    """
    if metadata is None:
        metadata = {}

    ensure_session(session_id)

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                json_dumps(metadata),
                now_text(),
            ),
        )

        conn.commit()

    finally:
        conn.close()


def save_qa_turn(
    session_id,
    question,
    answer,
    file_key="",
    file_names=None,
    task_info=None,
    route="",
    retrieval_question="",
    top_k="",
    candidate_top_n="",
    rerank_used=False,
    retrieved_sources=None,
    validation_result=None,
    was_repaired=False,
    elapsed_seconds=0,
    error="",
):
    """
    保存一轮完整问答。

    同时写入：
    1. qa_turns 表，便于分析每轮执行情况
    2. messages 表，便于恢复 chat_history
    """
    if file_names is None:
        file_names = []

    if task_info is None:
        task_info = {}

    if retrieved_sources is None:
        retrieved_sources = []

    if validation_result is None:
        validation_result = {}

    ensure_session(
        session_id=session_id,
        file_key=file_key,
        file_names=file_names,
    )

    conn = get_connection()

    try:
        cursor = conn.cursor()
        current_time = now_text()

        cursor.execute(
            """
            INSERT INTO qa_turns (
                session_id,
                question,
                answer,
                file_key,
                file_names,
                task_type,
                need_rag,
                answer_format,
                route,
                retrieval_question,
                top_k,
                candidate_top_n,
                rerank_used,
                retrieved_sources,
                validation_result,
                was_repaired,
                elapsed_seconds,
                error,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                question,
                answer,
                file_key,
                json_dumps(file_names),
                task_info.get("task_type", ""),
                str(task_info.get("need_rag", "")),
                task_info.get("answer_format", ""),
                route,
                retrieval_question,
                str(top_k),
                str(candidate_top_n),
                str(rerank_used),
                json_dumps(retrieved_sources),
                json_dumps(validation_result),
                1 if was_repaired else 0,
                float(elapsed_seconds or 0),
                error,
                current_time,
            ),
        )

        cursor.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                "user",
                question,
                json_dumps({
                    "file_key": file_key,
                    "file_names": file_names,
                }),
                current_time,
            ),
        )

        cursor.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                "assistant",
                answer,
                json_dumps({
                    "task_info": task_info,
                    "route": route,
                    "retrieval_question": retrieval_question,
                    "top_k": top_k,
                    "candidate_top_n": candidate_top_n,
                    "rerank_used": rerank_used,
                    "was_repaired": was_repaired,
                    "elapsed_seconds": elapsed_seconds,
                    "error": error,
                }),
                current_time,
            ),
        )

        cursor.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE session_id = ?
            """,
            (
                current_time,
                session_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def load_chat_history(session_id, limit=None):
    """
    读取某个 session 的聊天历史。

    返回格式：
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
    """
    if limit is None:
        limit = MEMORY_HISTORY_LIMIT

    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                session_id,
                limit,
            ),
        )

        rows = cursor.fetchall()
        rows = list(reversed(rows))

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
        ]

    finally:
        conn.close()


def get_session_turns(session_id, limit=50):
    """
    获取某个 session 的详细问答记录。
    """
    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM qa_turns
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                session_id,
                limit,
            ),
        )

        rows = cursor.fetchall()
        rows = list(reversed(rows))

        results = []

        for row in rows:
            item = dict(row)
            item["file_names"] = json_loads(item.get("file_names"), [])
            item["retrieved_sources"] = json_loads(item.get("retrieved_sources"), [])
            item["validation_result"] = json_loads(item.get("validation_result"), {})
            results.append(item)

        return results

    finally:
        conn.close()


def get_recent_sessions(limit=10):
    """
    获取最近的 session 列表。
    """
    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                s.session_id,
                s.file_key,
                s.file_names,
                s.created_at,
                s.updated_at,
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m
            ON s.session_id = m.session_id
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)
            item["file_names"] = json_loads(item.get("file_names"), [])
            results.append(item)

        return results

    finally:
        conn.close()


def clear_session_memory(session_id):
    """
    清空当前 session 的 memory。
    """
    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,),
        )

        cursor.execute(
            "DELETE FROM qa_turns WHERE session_id = ?",
            (session_id,),
        )

        cursor.execute(
            """
            UPDATE sessions
            SET updated_at = ?
            WHERE session_id = ?
            """,
            (
                now_text(),
                session_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def delete_session(session_id):
    """
    删除整个 session。
    """
    init_memory_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,),
        )

        cursor.execute(
            "DELETE FROM qa_turns WHERE session_id = ?",
            (session_id,),
        )

        cursor.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )

        conn.commit()

    finally:
        conn.close()