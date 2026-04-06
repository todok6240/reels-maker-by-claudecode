#!/usr/bin/env python3
"""
맛집 릴스 자동 생성기 - Flask 웹 서버
"""

import sys
# Windows cp949 환경에서 이모지 출력 시 인코딩 오류 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import glob
import uuid
import json
import threading
import logging
import colorlog
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, abort
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import redis

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

from database import init_db, list_restaurants, list_history, get_reel_path, get_reel_owner, save_restaurant, save_reel, save_captions
from make_reels import analyze_photos, generate_captions, make_reels

import time as _time
app = Flask(__name__)

# secret_key는 반드시 환경변수로 설정해야 함. 없으면 서버 시작 거부
_secret = os.environ.get("FLASK_SECRET_KEY")
if not _secret:
    raise RuntimeError("FLASK_SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
app.secret_key = _secret

CACHE_VER = str(int(_time.time()))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')

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

ADMIN_EMAILS = {"todok6240@gmail.com"}

TEMPLATES = {
    "food": {
        "name": "맛집/카페",
        "emoji": "🍜",
        "desc": "음식, 카페, 맛집 방문 후기",
        "gradient": "linear-gradient(135deg, #ff6b6b, #ee0979)",
        "accent": "#E52828",
        "visual": {"accent_color": [220, 40, 40], "text_position": "top", "overlay_opacity": 210},
    },
    "travel": {
        "name": "여행/관광",
        "emoji": "✈️",
        "desc": "여행지, 관광명소, 풍경 기록",
        "gradient": "linear-gradient(135deg, #667eea, #764ba2)",
        "accent": "#667eea",
        "visual": {"accent_color": [102, 126, 234], "text_position": "bottom", "overlay_opacity": 200},
    },
    "product": {
        "name": "상품 리뷰",
        "emoji": "🛍️",
        "desc": "제품, 쇼핑, 언박싱 리뷰",
        "gradient": "linear-gradient(135deg, #a18cd1, #fbc2eb)",
        "accent": "#7B2FBE",
        "visual": {"accent_color": [123, 47, 190], "text_position": "top", "overlay_opacity": 200},
    },
    "fitness": {
        "name": "운동/헬스",
        "emoji": "💪",
        "desc": "헬스장, 운동 루틴, 다이어트",
        "gradient": "linear-gradient(135deg, #f7971e, #ffd200)",
        "accent": "#E56A00",
        "visual": {"accent_color": [229, 106, 0], "text_position": "top", "overlay_opacity": 210},
    },
    "vlog": {
        "name": "일상/브이로그",
        "emoji": "🎬",
        "desc": "일상, 감성 브이로그, 데일리",
        "gradient": "linear-gradient(135deg, #11998e, #38ef7d)",
        "accent": "#1B9E6B",
        "visual": {"accent_color": [27, 158, 107], "text_position": "bottom", "overlay_opacity": 190},
    },
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("email") not in ADMIN_EMAILS:
            abort(403)
        return f(*args, **kwargs)
    return decorated

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# ── Redis 진행 상태 ───────────────────────────────────
_redis = redis.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    password=os.environ.get("REDIS_PASSWORD") or None,
    decode_responses=True,
)
PROGRESS_TTL = 60 * 60  # 1시간 후 자동 만료

def set_progress(sid: str, data: dict):
    _redis.setex(f"progress:{sid}", PROGRESS_TTL, json.dumps(data))

def get_progress(sid: str) -> dict:
    raw = _redis.get(f"progress:{sid}")
    return json.loads(raw) if raw else {"status": "idle", "message": ""}

def del_progress(sid: str):
    _redis.delete(f"progress:{sid}")


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
    # sid는 UUID 형식만 허용
    try:
        uuid.UUID(sid)
    except ValueError:
        abort(400)
    path = os.path.join(PHOTOS_DIR, sid)
    os.makedirs(path, exist_ok=True)
    return path


def session_output_dir(sid):
    try:
        uuid.UUID(sid)
    except ValueError:
        abort(400)
    path = os.path.join(OUTPUT_DIR, sid)
    os.makedirs(path, exist_ok=True)
    return path


def get_session_photos(sid):
    media_exts = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.heif",
                  "*.mp4", "*.mov", "*.avi", "*.m4v", "*.mkv", "*.3gp",
                  "*.JPG", "*.JPEG", "*.PNG", "*.MP4", "*.MOV")
    photos_dir = session_photos_dir(sid)
    seen = set()
    photos = []
    for ext in media_exts:
        for p in glob.glob(os.path.join(photos_dir, ext)):
            norm = os.path.normcase(p)
            if norm not in seen:
                seen.add(norm)
                photos.append(p)

    # Redis에 저장된 순서가 있으면 그 순서대로 반환
    saved_order_raw = _redis.get(f"photo_order:{sid}")
    if saved_order_raw:
        saved_order = json.loads(saved_order_raw)
        photo_map = {os.path.basename(p): p for p in photos}
        ordered = [photo_map[name] for name in saved_order if name in photo_map]
        # 순서에 없는 새 파일은 뒤에 추가
        ordered_names = set(saved_order)
        for p in photos:
            if os.path.basename(p) not in ordered_names:
                ordered.append(p)
        return ordered

    photos.sort()
    return photos


def clear_session_files(sid):
    """세션 사진 폴더 전체 삭제"""
    import shutil
    path = os.path.join(PHOTOS_DIR, sid)
    # 경로가 PHOTOS_DIR 안에 있는지 검증
    real_path = os.path.realpath(path)
    real_base = os.path.realpath(PHOTOS_DIR)
    if not real_path.startswith(real_base + os.sep):
        abort(400)
    if os.path.exists(path):
        shutil.rmtree(path)


def safe_join_check(base_dir, filename):
    """filename이 base_dir 안에 있는지 확인 후 경로 반환. 벗어나면 abort(400)"""
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(400)
    full_path = os.path.realpath(os.path.join(base_dir, safe_name))
    real_base = os.path.realpath(base_dir)
    if not full_path.startswith(real_base + os.sep):
        abort(400)
    return full_path, safe_name


@app.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("index"))
    login_bg = None
    for ext in ("jpg", "jpeg", "png", "webp"):
        candidate = os.path.join(BASE_DIR, "static", "images", f"login_bg.{ext}")
        if os.path.exists(candidate):
            login_bg = f"login_bg.{ext}"
            break
    return render_template("login.html", login_bg=login_bg)

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
    return render_template("dashboard.html", templates=TEMPLATES)


@app.route("/make")
@login_required
def make():
    template_id = request.args.get("t", "food")
    if template_id not in TEMPLATES:
        template_id = "food"
    get_session_id()
    return render_template("index.html", template_id=template_id, tmpl=TEMPLATES[template_id])


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
    # 소유권 확인: 이 reel이 현재 유저 것인지 검증
    user_id = get_user_id()
    owner = get_reel_owner(reel_id)
    if owner is None or owner != user_id:
        abort(403)

    path = get_reel_path(reel_id)
    if not path or not os.path.exists(path):
        return "파일을 찾을 수 없습니다.", 404

    # 경로가 OUTPUT_DIR 안에 있는지 검증
    real_path = os.path.realpath(path)
    real_base = os.path.realpath(OUTPUT_DIR)
    if not real_path.startswith(real_base + os.sep):
        abort(403)

    directory = os.path.dirname(path)
    filename  = os.path.basename(path)
    return send_from_directory(directory, filename, as_attachment=True)


@app.route("/stream/<int:reel_id>")
@login_required
def stream_reel(reel_id):
    user_id = get_user_id()
    owner = get_reel_owner(reel_id)
    if owner is None or owner != user_id:
        abort(403)

    path = get_reel_path(reel_id)
    if not path or not os.path.exists(path):
        return "파일을 찾을 수 없습니다.", 404

    real_path = os.path.realpath(path)
    real_base = os.path.realpath(OUTPUT_DIR)
    if not real_path.startswith(real_base + os.sep):
        abort(403)

    directory = os.path.dirname(path)
    filename  = os.path.basename(path)
    return send_from_directory(directory, filename, mimetype="video/mp4")


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
    del_progress(sid)
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
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTS:
            continue
        safe_name = secure_filename(f.filename)
        if not safe_name:
            continue
        dest = os.path.join(photos_dir, safe_name)
        f.save(dest)
        saved.append(safe_name)

    return jsonify({"uploaded": saved, "count": len(saved)})


@app.route("/api/thumbnail/<filename>")
def api_thumbnail(filename):
    """동영상 첫 프레임을 JPEG로 반환"""
    sid = get_session_id()
    photos_dir = session_photos_dir(sid)
    full_path, _ = safe_join_check(photos_dir, filename)
    if not os.path.exists(full_path):
        abort(404)

    from moviepy import VideoFileClip
    import io
    from PIL import Image as PILImage
    clip = VideoFileClip(full_path)
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
        from datetime import datetime
        ext = os.path.splitext(path)[1].lower()

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
                    dt_str = dt_str.replace("Z", "+00:00")
                    return datetime.fromisoformat(dt_str).timestamp()
            except Exception:
                pass
            return os.path.getmtime(path)

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
        return os.path.getmtime(path)

    sorted_photos = sorted(photos, key=get_capture_time)
    return jsonify([os.path.basename(p) for p in sorted_photos])


@app.route("/api/photos/delete", methods=["POST"])
def api_photos_delete():
    sid = get_session_id()
    filename = request.json.get("filename", "")
    photos_dir = session_photos_dir(sid)
    full_path, _ = safe_join_check(photos_dir, filename)
    if os.path.exists(full_path):
        os.remove(full_path)
    return jsonify({"ok": True})


@app.route("/api/photo/<filename>")
def api_photo(filename):
    sid = get_session_id()
    photos_dir = session_photos_dir(sid)
    _, safe_name = safe_join_check(photos_dir, filename)
    return send_from_directory(photos_dir, safe_name)


@app.route("/api/photos")
def api_photos():
    sid = get_session_id()
    photos = get_session_photos(sid)
    return jsonify([os.path.basename(p) for p in photos])


@app.route("/api/photos/reorder", methods=["POST"])
def api_photos_reorder():
    sid = get_session_id()
    data = request.json
    order = data.get("order", [])  # 파일명 배열
    _redis.setex(f"photo_order:{sid}", PROGRESS_TTL, json.dumps(order))
    return jsonify({"ok": True})


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
    # AI 원본 자막을 Redis에 보관 (make 단계에서 사용자 수정본과 함께 저장)
    _redis.setex(f"ai_captions:{sid}", PROGRESS_TTL, json.dumps(captions))
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

    ai_captions_raw = _redis.get(f"ai_captions:{sid}")
    ai_captions = json.loads(ai_captions_raw) if ai_captions_raw else None
    visual = TEMPLATES.get(content_type, TEMPLATES["food"])["visual"]

    def run():
        set_progress(sid, {"status": "running", "message": ""})
        try:
            output_path = make_reels(name, location, price, review, analysis, photos, captions,
                       output_dir=out_dir, visual=visual)
            restaurant_id = save_restaurant(user_id, name, location, price, review)
            reel_id = save_reel(restaurant_id, output_path, len(photos), user_id, content_type)
            save_captions(reel_id, photos, captions, ai_captions)
            set_progress(sid, {"status": "done", "message": "", "video_url": f"/stream/{reel_id}", "download_url": f"/download/{reel_id}"})
        except Exception as e:
            logging.error("영상 생성 실패: %s", e, exc_info=True)
            set_progress(sid, {"status": "error", "message": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"message": "생성 시작됨"})


@app.route("/api/progress")
def api_progress():
    sid = get_session_id()
    return jsonify(get_progress(sid))


@app.route("/output/<sid>/<filename>")
@login_required
def output_file(sid, filename):
    # 요청한 sid가 현재 세션의 sid와 일치하는지 확인
    my_sid = get_session_id()
    if sid != my_sid:
        abort(403)

    out_dir = os.path.join(OUTPUT_DIR, sid)
    _, safe_name = safe_join_check(out_dir, filename)
    return send_from_directory(out_dir, safe_name)


@app.route("/admin")
@admin_required
def admin():
    conn = __import__("database").get_conn()
    stats = {
        "total_reels":       conn.execute("SELECT COUNT(*) FROM reels").fetchone()[0],
        "total_restaurants": conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0],
        "total_users":       conn.execute("SELECT COUNT(DISTINCT owner_id) FROM reels WHERE owner_id NOT LIKE '________-____-____-____-____________'").fetchone()[0],
    }
    reels = conn.execute("""
        SELECT r.name, r.location, r.price, r.created_at,
               rl.id AS reel_id, rl.photo_count, rl.owner_id, rl.content_type
        FROM restaurants r
        LEFT JOIN reels rl ON rl.restaurant_id = r.id
        ORDER BY r.created_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return render_template("admin.html", stats=stats, reels=[dict(r) for r in reels])


if __name__ == "__main__":
    init_db()
    app.run(debug=False, port=5000)
