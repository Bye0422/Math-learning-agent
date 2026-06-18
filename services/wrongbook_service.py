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


WRONGBOOK_EXTRA_COLUMNS = {
    "mistake_reason": "TEXT DEFAULT ''",
    "review_status": "TEXT DEFAULT 'new'",
    "next_review_at": "TEXT DEFAULT ''",
    "last_reviewed_at": "TEXT DEFAULT ''",
    "review_count": "INTEGER DEFAULT 0",
    "card_html_path": "TEXT DEFAULT ''",
}


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

        ensure_wrongbook_extra_columns(cursor)

        conn.commit()

    finally:
        conn.close()


def ensure_wrongbook_extra_columns(cursor):
    cursor.execute("PRAGMA table_info(wrong_questions)")
    existing_columns = {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in cursor.fetchall()
    }

    for column_name, column_definition in WRONGBOOK_EXTRA_COLUMNS.items():
        if column_name in existing_columns:
            continue

        cursor.execute(
            f"ALTER TABLE wrong_questions ADD COLUMN {column_name} {column_definition}"
        )


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


def get_wrong_questions_by_ids(wrong_ids):
    """
    按 id 读取错题，并按传入 id 顺序返回。
    """
    if not wrong_ids:
        return []

    init_wrongbook_db()

    placeholders = ",".join(["?"] * len(wrong_ids))

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT *
            FROM wrong_questions
            WHERE id IN ({placeholders})
            """,
            tuple(wrong_ids),
        )

        rows = cursor.fetchall()
        by_id = {}

        for row in rows:
            item = dict(row)
            item["tags"] = json_loads(item.get("tags_json"), [])
            by_id[item["id"]] = item

        return [
            by_id[wrong_id]
            for wrong_id in wrong_ids
            if wrong_id in by_id
        ]

    finally:
        conn.close()


def get_wrong_questions_filtered(
    session_id=None,
    question_type="",
    difficulty=None,
    tag="",
    keyword="",
    review_status="",
    due_before=None,
    limit=200,
):
    """
    查询错题库，并在 Python 层做标签和关键词过滤。

    SQLite 表目前没有独立标签索引，先保持低风险实现。
    """
    questions = get_wrong_questions(session_id=session_id, limit=limit)

    if question_type:
        questions = [
            item
            for item in questions
            if item.get("type", "") == question_type
        ]

    if difficulty not in (None, "", "全部"):
        try:
            difficulty = int(difficulty)
            questions = [
                item
                for item in questions
                if int(item.get("difficulty", 0)) == difficulty
            ]
        except Exception:
            pass

    tag = str(tag or "").strip()

    if tag:
        questions = [
            item
            for item in questions
            if tag in item.get("tags", [])
        ]

    keyword = str(keyword or "").strip()

    if keyword:
        questions = [
            item
            for item in questions
            if (
                keyword in item.get("question_text", "")
                or keyword in item.get("analysis", "")
                or any(keyword in tag_item for tag_item in item.get("tags", []))
            )
        ]

    review_status = str(review_status or "").strip()

    if review_status and review_status != "全部":
        questions = [
            item
            for item in questions
            if item.get("review_status", "new") == review_status
        ]

    due_before = str(due_before or "").strip()

    if due_before:
        questions = [
            item
            for item in questions
            if item.get("next_review_at", "")
            and item.get("next_review_at", "") <= due_before
        ]

    return questions


def get_wrongbook_review_summary(session_id=None, due_before=None):
    """
    汇总错题本复习状态。
    """
    init_wrongbook_db()

    due_before = str(due_before or now_text()).strip()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        params = []
        session_where = ""

        if session_id:
            session_where = "WHERE session_id = ?"
            params.append(session_id)

        cursor.execute(
            f"""
            SELECT
                COALESCE(review_status, 'new') AS review_status,
                COUNT(*) AS cnt,
                COALESCE(SUM(review_count), 0) AS review_count_sum
            FROM wrong_questions
            {session_where}
            GROUP BY COALESCE(review_status, 'new')
            """,
            tuple(params),
        )

        by_status = {}
        total_questions = 0
        total_review_count = 0

        for row in cursor.fetchall():
            status = row["review_status"] or "new"
            count = int(row["cnt"])
            review_count_sum = int(row["review_count_sum"] or 0)

            by_status[status] = count
            total_questions += count
            total_review_count += review_count_sum

        due_params = []
        due_where = "WHERE next_review_at != '' AND next_review_at <= ?"
        due_params.append(due_before)

        if session_id:
            due_where += " AND session_id = ?"
            due_params.append(session_id)

        cursor.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM wrong_questions
            {due_where}
            """,
            tuple(due_params),
        )

        due_count = int(cursor.fetchone()["cnt"])

        return {
            "by_status": by_status,
            "due_count": due_count,
            "total_questions": total_questions,
            "total_review_count": total_review_count,
        }

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


def update_wrong_question_review(
    wrong_id,
    mistake_reason=None,
    review_status=None,
    next_review_at=None,
    last_reviewed_at=None,
):
    """
    更新错题复习信息。
    """
    init_wrongbook_db()

    updates = []
    params = []

    if mistake_reason is not None:
        updates.append("mistake_reason = ?")
        params.append(mistake_reason)

    if review_status is not None:
        updates.append("review_status = ?")
        params.append(review_status)

    if next_review_at is not None:
        updates.append("next_review_at = ?")
        params.append(next_review_at)

    if last_reviewed_at is not None:
        updates.append("last_reviewed_at = ?")
        params.append(last_reviewed_at)
        updates.append("review_count = review_count + 1")

    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(now_text())
    params.append(wrong_id)

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE wrong_questions
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            tuple(params),
        )
        conn.commit()
        return cursor.rowcount > 0

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


def export_wrong_questions_to_pdf_by_ids(wrong_ids):
    """
    将指定错题 id 对应的图片批量导出为 PDF。
    """
    questions = get_wrong_questions_by_ids(wrong_ids)

    image_paths = []

    for q in questions:
        path = q.get("card_image_path", "")

        if path and Path(path).exists():
            image_paths.append(path)

    if not image_paths:
        raise ValueError("选中的错题中没有可导出的错题卡图片。")

    images = []

    for path in image_paths:
        img = Image.open(path).convert("RGB")
        images.append(img)

    output_dir = ensure_pdf_output_dir()
    pdf_path = output_dir / f"wrongbook_selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

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
