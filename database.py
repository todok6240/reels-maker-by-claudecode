#!/usr/bin/env python3
"""
SQLite 데이터베이스 관리
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/reels_maker/reels.db")


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
            created_at    TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );

        CREATE TABLE IF NOT EXISTS captions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id        INTEGER NOT NULL,
            order_index    INTEGER NOT NULL,
            photo_filename TEXT,
            caption_text   TEXT,
            FOREIGN KEY (reel_id) REFERENCES reels(id)
        );
    """)
    # 기존 DB에 owner_id 컬럼이 없으면 추가 (마이그레이션)
    try:
        conn.execute("ALTER TABLE reels ADD COLUMN owner_id TEXT")
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


def save_reel(restaurant_id: int, output_path: str, photo_count: int, owner_id: str = None) -> int:
    """릴스 정보 저장 후 ID 반환"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO reels (restaurant_id, output_path, photo_count, owner_id) VALUES (?, ?, ?, ?)",
        (restaurant_id, output_path, photo_count, owner_id)
    )
    reel_id = cur.lastrowid
    conn.commit()
    conn.close()
    return reel_id


def save_captions(reel_id: int, photos: list, captions: list):
    """자막 목록 저장"""
    import os as _os
    conn = get_conn()
    for i, (photo, caption) in enumerate(zip(photos, captions)):
        conn.execute(
            "INSERT INTO captions (reel_id, order_index, photo_filename, caption_text) VALUES (?, ?, ?, ?)",
            (reel_id, i + 1, _os.path.basename(photo), caption)
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
