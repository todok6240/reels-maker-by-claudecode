#!/usr/bin/env python3
"""
맛집 릴스 자동 생성기 - Flask 웹 서버
"""

import os
import glob
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database import init_db, list_restaurants
from make_reels import analyze_photos, generate_captions, make_reels, get_photos

app = Flask(__name__)

PHOTOS_DIR = os.path.expanduser("~/reels_maker/photos")
OUTPUT_DIR = os.path.expanduser("~/reels_maker/output")

# 진행 상태 공유 (간단한 in-memory)
progress = {"status": "idle", "message": ""}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history():
    restaurants = list_restaurants()
    return render_template("history.html", restaurants=restaurants)


@app.route("/api/photos")
def api_photos():
    exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    photos = []
    for ext in exts:
        photos.extend(glob.glob(os.path.join(PHOTOS_DIR, ext)))
    photos.sort()
    return jsonify([os.path.basename(p) for p in photos])


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    photos = get_photos()
    if not photos:
        return jsonify({"error": "사진이 없습니다."}), 400
    analysis = analyze_photos(photos)
    return jsonify({"analysis": analysis, "photos": [os.path.basename(p) for p in photos]})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json
    name     = data.get("name", "")
    location = data.get("location", "")
    price    = data.get("price", "")
    review   = data.get("review", "")
    analysis = data.get("analysis", "")
    order    = data.get("order", [])

    photos = get_photos()
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    captions = generate_captions(name, location, price, review, analysis, photos)
    return jsonify({"captions": captions, "photos": [os.path.basename(p) for p in photos]})


@app.route("/api/make", methods=["POST"])
def api_make():
    data     = request.json
    name     = data.get("name", "")
    location = data.get("location", "")
    price    = data.get("price", "")
    review   = data.get("review", "")
    analysis = data.get("analysis", "")
    captions = data.get("captions", [])
    order    = data.get("order", [])

    photos = get_photos()
    if order:
        photos = [photos[i] for i in order if 0 <= i < len(photos)]

    def run():
        progress["status"] = "running"
        progress["message"] = "영상 생성 중..."
        try:
            make_reels(name, location, price, review, analysis, photos, captions)
            progress["status"] = "done"
            progress["message"] = "완료!"
        except Exception as e:
            progress["status"] = "error"
            progress["message"] = str(e)

    threading.Thread(target=run).start()
    return jsonify({"message": "생성 시작됨"})


@app.route("/api/progress")
def api_progress():
    return jsonify(progress)


@app.route("/output/<filename>")
def output_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
