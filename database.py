#!/usr/bin/env python3
"""
SQLite 데이터베이스 관리
"""

import sqlite3
import os
from datetime import datetime
from crypto import encrypt, decrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reels.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """테이블 초기화"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            name       TEXT NOT NULL,
            location   TEXT NOT NULL,
            price      TEXT,
            review     TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS reels (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            output_path   TEXT,
            photo_count   INTEGER,
            owner_id      TEXT,
            content_type  TEXT,
            created_at    TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );

        CREATE TABLE IF NOT EXISTS captions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id          INTEGER NOT NULL,
            order_index      INTEGER NOT NULL,
            photo_filename   TEXT,
            ai_caption_text  TEXT,
            caption_text     TEXT,
            FOREIGN KEY (reel_id) REFERENCES reels(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            google_sub TEXT UNIQUE NOT NULL,
            email_enc  TEXT NOT NULL,
            name_enc   TEXT NOT NULL,
            picture    TEXT,
            is_allowed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            last_login TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS admin_access_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ip         TEXT NOT NULL,
            user_agent TEXT,
            user_email TEXT,
            result     TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)
    # 마이그레이션: 누락된 컬럼 추가
    for migration in [
        "ALTER TABLE reels ADD COLUMN owner_id TEXT",
        "ALTER TABLE reels ADD COLUMN content_type TEXT",
        "ALTER TABLE captions ADD COLUMN ai_caption_text TEXT",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except Exception:
            pass  # 이미 존재하면 무시
    conn.commit()
    conn.close()


def save_restaurant(session_id: str, name: str, location: str, price: str, review: str) -> int:
    """맛집 정보 저장 후 ID 반환"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO restaurants (session_id, name, location, price, review) VALUES (?, ?, ?, ?, ?)",
        (session_id, name, location, price, review)
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def save_reel(restaurant_id: int, output_path: str, photo_count: int, owner_id: str = None, content_type: str = None) -> int:
    """릴스 정보 저장 후 ID 반환"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO reels (restaurant_id, output_path, photo_count, owner_id, content_type) VALUES (?, ?, ?, ?, ?)",
        (restaurant_id, output_path, photo_count, owner_id, content_type)
    )
    reel_id = cur.lastrowid
    conn.commit()
    conn.close()
    return reel_id


def save_captions(reel_id: int, photos: list, captions: list, ai_captions: list = None):
    """자막 목록 저장. ai_captions가 있으면 AI 원본과 사용자 수정본 모두 저장."""
    import os as _os
    conn = get_conn()
    for i, (photo, caption) in enumerate(zip(photos, captions)):
        ai_text = ai_captions[i] if ai_captions and i < len(ai_captions) else None
        conn.execute(
            "INSERT INTO captions (reel_id, order_index, photo_filename, ai_caption_text, caption_text) VALUES (?, ?, ?, ?, ?)",
            (reel_id, i + 1, _os.path.basename(photo), ai_text, caption)
        )
    conn.commit()
    conn.close()


def list_restaurants(session_id: str = None):
    """저장된 맛집 목록 반환 (session_id 있으면 해당 세션만)"""
    conn = get_conn()
    if session_id:
        rows = conn.execute(
            "SELECT id, session_id, name, location, price, created_at FROM restaurants WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, session_id, name, location, price, created_at FROM restaurants ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return rows


def list_history(user_id: str):
    """Google 유저 기준 히스토리 (reels JOIN 포함)"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT r.id, r.name, r.location, r.price, r.created_at,
               rl.id AS reel_id, rl.output_path, rl.photo_count
        FROM restaurants r
        LEFT JOIN reels rl ON rl.restaurant_id = r.id
        WHERE r.session_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def get_reel_path(reel_id: int) -> str:
    """reel_id로 output_path 반환"""
    conn = get_conn()
    row = conn.execute("SELECT output_path FROM reels WHERE id = ?", (reel_id,)).fetchone()
    conn.close()
    return row["output_path"] if row else None


def get_reel_owner(reel_id: int) -> str:
    """reel_id의 소유자 ID 반환 (소유권 확인용)"""
    conn = get_conn()
    row = conn.execute("SELECT owner_id FROM reels WHERE id = ?", (reel_id,)).fetchone()
    conn.close()
    return row["owner_id"] if row else None


# ── users 테이블 ──────────────────────────────────────

def upsert_user(google_sub: str, email: str, name: str, picture: str):
    """Google 로그인 시 유저 등록 또는 last_login 갱신"""
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM users WHERE google_sub = ?", (google_sub,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET last_login = datetime('now','localtime'), picture = ? WHERE google_sub = ?",
            (picture, google_sub)
        )
    else:
        conn.execute(
            "INSERT INTO users (google_sub, email_enc, name_enc, picture, is_allowed) VALUES (?, ?, ?, ?, 0)",
            (google_sub, encrypt(email), encrypt(name), picture)
        )
    conn.commit()
    conn.close()


def is_user_allowed(google_sub: str) -> bool:
    """유저가 허용 상태인지 확인"""
    conn = get_conn()
    row = conn.execute(
        "SELECT is_allowed FROM users WHERE google_sub = ?", (google_sub,)
    ).fetchone()
    conn.close()
    return bool(row["is_allowed"]) if row else False


def set_user_allowed(user_id: int, allowed: bool):
    """유저 허용 상태 변경"""
    conn = get_conn()
    conn.execute("UPDATE users SET is_allowed = ? WHERE id = ?", (1 if allowed else 0, user_id))
    conn.commit()
    conn.close()


def log_admin_access(ip: str, user_agent: str, user_email: str, result: str):
    """관리자 페이지 접근 시도 기록"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO admin_access_log (ip, user_agent, user_email, result) VALUES (?, ?, ?, ?)",
        (ip, user_agent, user_email, result)
    )
    conn.commit()
    conn.close()


def list_admin_access_log() -> list:
    """관리자 접근 로그 반환 (최근 200건)"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, ip, user_agent, user_email, result, created_at FROM admin_access_log ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_users() -> list:
    """모든 유저 목록 반환 (복호화 포함)"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, google_sub, email_enc, name_enc, picture, is_allowed, created_at, last_login FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id":         r["id"],
            "google_sub": r["google_sub"],
            "email":      decrypt(r["email_enc"]),
            "name":       decrypt(r["name_enc"]),
            "picture":    r["picture"],
            "is_allowed": r["is_allowed"],
            "created_at": r["created_at"],
            "last_login": r["last_login"],
        })
    return result
