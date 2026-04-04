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
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            location  TEXT NOT NULL,
            price     TEXT,
            review    TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS reels (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            output_path   TEXT,
            photo_count   INTEGER,
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
    conn.commit()
    conn.close()


def save_restaurant(name: str, location: str, price: str, review: str) -> int:
    """맛집 정보 저장 후 ID 반환"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO restaurants (name, location, price, review) VALUES (?, ?, ?, ?)",
        (name, location, price, review)
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid


def save_reel(restaurant_id: int, output_path: str, photo_count: int) -> int:
    """릴스 정보 저장 후 ID 반환"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO reels (restaurant_id, output_path, photo_count) VALUES (?, ?, ?)",
        (restaurant_id, output_path, photo_count)
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


def list_restaurants():
    """저장된 맛집 목록 출력"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, location, price, created_at FROM restaurants ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows
