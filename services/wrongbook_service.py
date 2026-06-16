import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image

from config import (
    WRONGBOOK_DB_PATH,
    WRONGBOOK_PDF_OUTPUT_DIR,
)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_dumps(data):
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return json.dumps(str(data), ensure_ascii=False)


def json_loads(text, default=None):
    if default is None:
        default = []

    if not text:
        return default

    try:
        return json.loads(text)
    except Exception:
        return default


def get_wrongbook_db_path():
    db_path = Path(WRONGBOOK_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection():
    conn = sqlite3.connect(str(get_wrongbook_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_wrongbook_db():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                question_text TEXT NOT NULL,
                analysis TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                type TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                source_file TEXT,
                source_location TEXT,
                source_chunk_id TEXT,
                card_image_path TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wrong_questions_session_id
            ON wrong_questions(session_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wrong_questions_type
            ON wrong_questions(type)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wrong_questions_difficulty
            ON wrong_questions(difficulty)
            """
        )

        conn.commit()

    finally:
        conn.close()


def save_wrong_question(
    session_id,
    question_text,
    item,
    card_image_path,
    source_info=None,
):
    """
    保存一道错题。
    """
    if source_info is None:
        source_info = {}

    init_wrongbook_db()

    wrong_id = uuid.uuid4().hex[:16]
    current_time = now_text()

    tags = item.get("tags", [])

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO wrong_questions (
                id,
                session_id,
                question_text,
                analysis,
                difficulty,
                type,
                tags_json,
                source_file,
                source_location,
                source_chunk_id,
                card_image_path,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                wrong_id,
                session_id,
                question_text,
                item.get("analysis", ""),
                int(item.get("difficulty", 2)),
                item.get("type", "计算题"),
                json_dumps(tags),
                source_info.get("source_file", ""),
                source_info.get("source_location", ""),
                source_info.get("source_chunk_id", ""),
                card_image_path,
                current_time,
                current_time,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    return wrong_id


def save_wrong_question_cards(
    session_id,
    card_results,
    source_info=None,
):
    """
    批量保存本轮生成的错题卡。
    """
    saved_ids = []

    for card in card_results:
        wrong_id = save_wrong_question(
            session_id=session_id,
            question_text=card.get("question_text", ""),
            item=card.get("item", {}),
            card_image_path=card.get("image_path", ""),
            source_info=source_info,
        )

        saved_ids.append(wrong_id)

    return saved_ids


def get_wrong_questions(session_id=None, limit=200):
    """
    读取错题库。
    """
    init_wrongbook_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                """
                SELECT *
                FROM wrong_questions
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    session_id,
                    limit,
                ),
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM wrong_questions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)
            item["tags"] = json_loads(item.get("tags_json"), [])
            results.append(item)

        return results

    finally:
        conn.close()


def count_wrong_questions(session_id=None):
    init_wrongbook_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM wrong_questions WHERE session_id = ?",
                (session_id,),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM wrong_questions"
            )

        row = cursor.fetchone()
        return int(row["cnt"])

    finally:
        conn.close()


def delete_wrong_question(wrong_id):
    init_wrongbook_db()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM wrong_questions WHERE id = ?",
            (wrong_id,),
        )

        conn.commit()

    finally:
        conn.close()


def ensure_pdf_output_dir():
    output_dir = Path(WRONGBOOK_PDF_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def export_wrong_questions_to_pdf(session_id=None):
    """
    将错题库中的图片批量导出为 PDF。
    """
    questions = get_wrong_questions(
        session_id=session_id,
        limit=1000,
    )

    image_paths = []

    for q in questions:
        path = q.get("card_image_path", "")

        if path and Path(path).exists():
            image_paths.append(path)

    if not image_paths:
        raise ValueError("错题库中没有可导出的错题卡图片。")

    images = []

    for path in image_paths:
        img = Image.open(path).convert("RGB")
        images.append(img)

    output_dir = ensure_pdf_output_dir()
    pdf_path = output_dir / f"wrongbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    first_image = images[0]
    rest_images = images[1:]

    first_image.save(
        pdf_path,
        save_all=True,
        append_images=rest_images,
        resolution=150,
    )

    for img in images:
        img.close()

    return str(pdf_path)


def build_wrong_question_summary(question):
    tags = question.get("tags", [])

    return {
        "id": question.get("id", ""),
        "type": question.get("type", ""),
        "difficulty": question.get("difficulty", ""),
        "tags": tags,
        "created_at": question.get("created_at", ""),
        "card_image_path": question.get("card_image_path", ""),
    }