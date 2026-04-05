#!/usr/bin/env python3
"""
맛집 릴스 자동 생성기 - Flask 웹 서버
"""

import os
import glob
import uuid
import threading
import logging
import colorlog
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── 컬러 로깅 설정 ────────────────────────────────────
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s[%(levelname)s]%(reset)s %(message)s",
    log_colors={
        "DEBUG":    "cyan",
        "INFO":     "green",
        "WARNING":  "yellow",
        "ERROR":    "red",
        "CRITICAL": "bold_red",
    }
))
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("werkzeug").setLevel(logging.INFO)

from database import init_db, list_restaurants, list_history, get_reel_path, save_restaurant, save_reel, save_captions
from make_reels import analyze_photos, generate_captions, make_reels

import time as _time
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "reels-maker-secret-2024")

CACHE_VER = str(int(_time.time()))

@app.context_processor
def inject_cache_ver():
    return {"cache_ver": CACHE_VER, "current_user": session.get("user")}

# ── Google OAuth ──────────────────────────────────────
oauth = OAuth(app)
google_oauth = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

BASE_DIR   = os.path.expanduser("~/reels_maker")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 세션별 진행 상태
progress_map = {}


def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def get_user_id():
    """Google 로그인이면 email, 게스트면 session UUID 반환"""
    user = session.get("user")
    if user and user.get("type") == "google":
        return user.get("email")
    return get_session_id()


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


@app.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/auth/guest", methods=["POST"])
def auth_guest():
    session["user"] = {"type": "guest", "name": "게스트"}
    return redirect(url_for("index"))

@app.route("/auth/google")
def auth_google():
    redirect_uri = url_for("auth_google_callback", _external=True)
    return google_oauth.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def auth_google_callback():
    token = google_oauth.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        return redirect(url_for("login"))
    session["user"] = {
        "type": "google",
        "name": userinfo.get("name", ""),
        "email": userinfo.get("email", ""),
        "picture": userinfo.get("picture", ""),
    }
    return redirect(url_for("index"))

@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@app.route("/")
@login_required
def index():
    get_session_id()
    return render_template("index.html")


@app.route("/history")
@login_required
def history():
    user = session.get("user", {})
    if user.get("type") != "google":
        return redirect(url_for("index"))
    user_id = user.get("email")
    rows = list_history(user_id)
    return render_template("history.html", rows=rows)


@app.route("/download/<int:reel_id>")
@login_required
def download_reel(reel_id):
    path = get_reel_path(reel_id)
    if not path or not os.path.exists(path):
        return "파일을 찾을 수 없습니다.", 404
    directory = os.path.dirname(path)
    filename  = os.path.basename(path)
    return send_from_directory(directory, filename, as_attachment=True)


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

    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".m4v", ".mkv", ".3gp"}
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}

    def get_capture_time(path):
        import subprocess, json
        from datetime import datetime, timezone
        ext = os.path.splitext(path)[1].lower()

        # 동영상: ffprobe로 creation_time 메타데이터 추출
        if ext in VIDEO_EXTS:
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_entries", "format_tags=creation_time", path],
                    capture_output=True, text=True, timeout=10
                )
                data = json.loads(result.stdout)
                dt_str = data.get("format", {}).get("tags", {}).get("creation_time", "")
                if dt_str:
                    # ISO 8601 형식: "2024-01-15T14:30:00.000000Z"
                    dt_str = dt_str.replace("Z", "+00:00")
                    return datetime.fromisoformat(dt_str).timestamp()
            except Exception:
                pass
            return os.path.getmtime(path)

        # 사진: EXIF DateTimeOriginal 우선
        if ext in IMAGE_EXTS:
            try:
                from PIL import Image as PILImage
                img = PILImage.open(path)
                exif = img._getexif() if hasattr(img, "_getexif") else None
                if exif:
                    dt_str = exif.get(36867) or exif.get(306)
                    if dt_str:
                        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").timestamp()
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
    data         = request.json
    name         = data.get("name", "")
    location     = data.get("location", "")
    price        = data.get("price", "")
    review       = data.get("review", "")
    analysis     = data.get("analysis", "")
    order        = data.get("order", [])
    content_type = data.get("content_type", "food")

    photos = get_session_photos(sid)
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    captions = generate_captions(name, location, price, review, analysis, photos, content_type)
    return jsonify({"captions": captions, "photos": [os.path.basename(p) for p in photos]})


@app.route("/api/make", methods=["POST"])
def api_make():
    sid      = get_session_id()
    user_id  = get_user_id()
    data         = request.json
    name         = data.get("name", "")
    location     = data.get("location", "")
    price        = data.get("price", "")
    review       = data.get("review", "")
    analysis     = data.get("analysis", "")
    captions     = data.get("captions", [])
    order        = data.get("order", [])
    content_type = data.get("content_type", "food")

    photos = get_session_photos(sid)
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    out_dir = session_output_dir(sid)

    def run():
        progress_map[sid] = {"status": "running", "message": "영상 생성 중..."}
        try:
            make_reels(name, location, price, review, analysis, photos, captions,
                       output_dir=out_dir)
            restaurant_id = save_restaurant(user_id, name, location, price, review)
            safe_name = name.replace(" ", "_")
            output_path = os.path.join(out_dir, f"{safe_name}_reels.mp4")
            reel_id = save_reel(restaurant_id, output_path, len(photos))
            save_captions(reel_id, photos, captions)
            safe_filename = f"{safe_name}_reels.mp4"
            video_url = f"/output/{sid}/{safe_filename}"
            progress_map[sid] = {"status": "done", "message": "완료!", "video_url": video_url}
        except Exception as e:
            logging.error("영상 생성 실패: %s", e, exc_info=True)
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
