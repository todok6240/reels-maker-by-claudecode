#!/usr/bin/env python3
"""
맛집 릴스 자동 생성기 - Flask 웹 서버
"""

import os
import glob
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database import init_db, list_restaurants, save_restaurant, save_reel, save_captions
from make_reels import analyze_photos, generate_captions, make_reels

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "reels-maker-secret-2024")

BASE_DIR   = os.path.expanduser("~/reels_maker")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 세션별 진행 상태
progress_map = {}


def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def session_photos_dir(sid):
    path = os.path.join(PHOTOS_DIR, sid)
    os.makedirs(path, exist_ok=True)
    return path


def session_output_dir(sid):
    path = os.path.join(OUTPUT_DIR, sid)
    os.makedirs(path, exist_ok=True)
    return path


def get_session_photos(sid):
    media_exts = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.heif",
                  "*.mp4", "*.mov", "*.avi", "*.m4v", "*.mkv", "*.3gp",
                  "*.JPG", "*.JPEG", "*.PNG", "*.MP4", "*.MOV")
    photos = []
    for ext in media_exts:
        photos.extend(glob.glob(os.path.join(session_photos_dir(sid), ext)))
    photos.sort()
    return photos


def clear_session_files(sid):
    """세션 사진 폴더 전체 삭제"""
    import shutil
    path = os.path.join(PHOTOS_DIR, sid)
    if os.path.exists(path):
        shutil.rmtree(path)


@app.route("/")
def index():
    get_session_id()
    return render_template("index.html")


@app.route("/history")
def history():
    sid = get_session_id()
    restaurants = list_restaurants(sid)
    return render_template("history.html", restaurants=restaurants)


@app.route("/api/session")
def api_session():
    sid = get_session_id()
    photos = [os.path.basename(p) for p in get_session_photos(sid)]
    status = "working" if photos else "idle"
    return jsonify({"session_id": sid, "status": status, "photos": photos})


@app.route("/api/session/reset", methods=["POST"])
def api_session_reset():
    sid = get_session_id()
    clear_session_files(sid)
    session["work_status"] = "idle"
    return jsonify({"ok": True})


ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif",
                ".mp4", ".mov", ".avi", ".m4v", ".mkv", ".3gp"}

@app.route("/api/upload", methods=["POST"])
def api_upload():
    sid = get_session_id()
    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "파일이 없습니다."}), 400

    saved = []
    photos_dir = session_photos_dir(sid)
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower() if f.filename else ""
        if f.filename and ext in ALLOWED_EXTS:
            dest = os.path.join(photos_dir, f.filename)
            f.save(dest)
            saved.append(f.filename)

    return jsonify({"uploaded": saved, "count": len(saved)})


@app.route("/api/thumbnail/<filename>")
def api_thumbnail(filename):
    """동영상 첫 프레임을 JPEG로 반환"""
    sid = get_session_id()
    path = os.path.join(session_photos_dir(sid), filename)
    from moviepy import VideoFileClip
    import io
    from PIL import Image as PILImage
    clip = VideoFileClip(path)
    frame = clip.get_frame(0)
    clip.close()
    img = PILImage.fromarray(frame)
    img.thumbnail((200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="image/jpeg")


@app.route("/api/photos/sort-by-time")
def api_sort_by_time():
    sid = get_session_id()
    photos = get_session_photos(sid)

    def get_capture_time(path):
        ext = os.path.splitext(path)[1].lower()
        # 사진: EXIF DateTimeOriginal 우선
        if ext in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
            try:
                from PIL import Image as PILImage
                img = PILImage.open(path)
                exif = img._getexif()
                if exif:
                    # 36867 = DateTimeOriginal
                    dt_str = exif.get(36867) or exif.get(306)
                    if dt_str:
                        from datetime import datetime
                        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
        # 폴백: 파일 수정 시간
        return os.path.getmtime(path)

    sorted_photos = sorted(photos, key=get_capture_time)
    return jsonify([os.path.basename(p) for p in sorted_photos])


@app.route("/api/photos/delete", methods=["POST"])
def api_photos_delete():
    sid = get_session_id()
    filename = request.json.get("filename")
    path = os.path.join(session_photos_dir(sid), filename)
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"ok": True})


@app.route("/api/photo/<filename>")
def api_photo(filename):
    sid = get_session_id()
    return send_from_directory(session_photos_dir(sid), filename)


@app.route("/api/photos")
def api_photos():
    sid = get_session_id()
    photos = get_session_photos(sid)
    return jsonify([os.path.basename(p) for p in photos])


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    sid = get_session_id()
    photos = get_session_photos(sid)
    if not photos:
        return jsonify({"error": "사진이 없습니다."}), 400
    analysis = analyze_photos(photos)
    return jsonify({"analysis": analysis, "photos": [os.path.basename(p) for p in photos]})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    sid = get_session_id()
    data     = request.json
    name     = data.get("name", "")
    location = data.get("location", "")
    price    = data.get("price", "")
    review   = data.get("review", "")
    analysis = data.get("analysis", "")
    order    = data.get("order", [])

    photos = get_session_photos(sid)
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    captions = generate_captions(name, location, price, review, analysis, photos)
    return jsonify({"captions": captions, "photos": [os.path.basename(p) for p in photos]})


@app.route("/api/make", methods=["POST"])
def api_make():
    sid      = get_session_id()
    data     = request.json
    name     = data.get("name", "")
    location = data.get("location", "")
    price    = data.get("price", "")
    review   = data.get("review", "")
    analysis = data.get("analysis", "")
    captions = data.get("captions", [])
    order    = data.get("order", [])

    photos = get_session_photos(sid)
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    out_dir = session_output_dir(sid)

    def run():
        progress_map[sid] = {"status": "running", "message": "영상 생성 중..."}
        try:
            make_reels(name, location, price, review, analysis, photos, captions,
                       output_dir=out_dir)
            restaurant_id = save_restaurant(sid, name, location, price, review)
            safe_name = name.replace(" ", "_")
            output_path = os.path.join(out_dir, f"{safe_name}_reels.mp4")
            reel_id = save_reel(restaurant_id, output_path, len(photos))
            save_captions(reel_id, photos, captions)
            progress_map[sid] = {"status": "done", "message": "완료!"}
        except Exception as e:
            progress_map[sid] = {"status": "error", "message": str(e)}

    threading.Thread(target=run).start()
    return jsonify({"message": "생성 시작됨"})


@app.route("/api/progress")
def api_progress():
    sid = get_session_id()
    return jsonify(progress_map.get(sid, {"status": "idle", "message": ""}))


@app.route("/output/<sid>/<filename>")
def output_file(sid, filename):
    return send_from_directory(os.path.join(OUTPUT_DIR, sid), filename)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
