#!/usr/bin/env python3
"""
맛집 릴스 자동 생성기
사용법: python make_reels.py
"""

import os
import sys
import glob
import random
import base64
import anthropic
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy import ImageSequenceClip, AudioFileClip
import numpy as np

# ── 설정 ──────────────────────────────────────────────
PHOTOS_DIR = os.path.expanduser("~/reels_maker/photos")
OUTPUT_DIR = os.path.expanduser("~/reels_maker/output")
BGM_DIR    = os.path.expanduser("~/reels_maker/bgm")

REELS_W, REELS_H = 1080, 1920   # 세로형 릴스 해상도
PHOTO_DURATION   = 3.0           # 사진 1장당 표시 시간(초)
BGM_VOLUME       = 0.3           # BGM 볼륨 (0.0 ~ 1.0)
# ─────────────────────────────────────────────────────


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("❌ ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    return key


def encode_image(photo_path: str) -> tuple[str, str]:
    """이미지를 분석용으로 축소 후 base64 인코딩 (최대 1280px, 5MB 이하)"""
    img = Image.open(photo_path).convert("RGB")
    max_size = 1280
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return data, "image/jpeg"


def analyze_photos(photos: list[str]) -> dict:
    """Claude Vision으로 사진 분석 후 피드백 반환"""
    client = anthropic.Anthropic(api_key=get_api_key())

    # 분석용 이미지 콘텐츠 구성 (최대 5장으로 요약 분석)
    sample = photos[:5] if len(photos) > 5 else photos
    content = []

    for i, path in enumerate(sample):
        data, media_type = encode_image(path)
        content.append({
            "type": "text",
            "text": f"[사진 {i+1}/{len(photos)}] {os.path.basename(path)}"
        })
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data}
        })

    content.append({
        "type": "text",
        "text": f"""총 {len(photos)}장의 맛집 사진입니다 (앞의 {len(sample)}장 분석).

다음 3가지를 분석해줘:

1. **각 사진 설명**: 어떤 음식인지, 어떤 장면인지 한 줄씩
2. **추천 사진 순서**: 릴스 흐름상 어떤 순서로 배치하면 좋을지 (번호로)
3. **콘텐츠 방향 제안**: 이 사진들로 어떤 스토리를 만들면 좋을지

한국어로 답변해줘."""
    })

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": content}]
    )

    return message.content[0].text


def generate_captions(name: str, location: str, price: str, review: str,
                      analysis: str, photo_order: list[str]) -> list[str]:
    """Claude API로 자막 생성"""
    client = anthropic.Anthropic(api_key=get_api_key())

    photo_count = len(photo_order)
    filenames = "\n".join([f"{i+1}. {os.path.basename(p)}" for i, p in enumerate(photo_order)])

    prompt = f"""맛집 인스타그램 릴스용 자막을 {photo_count}개 만들어줘.

맛집 정보:
- 이름: {name}
- 위치: {location}
- 가격대: {price}
- 총평: {review}

사진 분석 결과:
{analysis}

사진 순서 ({photo_count}장):
{filenames}

자막 구성 규칙:
- 1번째 사진: 맛집 이름 + 위치 (예: "홍대 스기모토 라멘")
- 중간 사진들: 음식/분위기 설명 (감성적으로)
- 마지막 사진: 가격대 + 한 줄 총평

조건:
- 번호나 따옴표 없이 자막만 한 줄씩
- 정확히 {photo_count}줄
- 한국어
- 이모티콘, 특수문자 절대 사용 금지 (텍스트만)
- 각 자막은 반드시 12자 이내 (공백 포함)"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    lines = message.content[0].text.strip().split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    while len(lines) < photo_count:
        lines.append(name)

    return lines[:photo_count]


def fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """이미지를 릴스 해상도에 맞게 크롭/리사이즈"""
    img = img.convert("RGB")
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def draw_caption(img: Image.Image, text: str) -> Image.Image:
    """이미지 하단에 그라디언트 페이드 + 자막 추가"""
    img = img.convert("RGBA")
    w, h = img.size

    # 상단 35% 영역에 비선형 그라디언트 오버레이 생성
    grad_h = int(h * 0.35)
    gradient = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(grad_h):
        alpha = int(210 * ((grad_h - y) / grad_h) ** 1.8)
        gradient[y, :, 3] = alpha

    overlay = Image.fromarray(gradient, "RGBA")
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",   # 모던한 산세리프
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/NanumGothicBold.ttf",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size=62)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    # 텍스트가 이미지 너비를 넘으면 단어 단위로 줄바꿈
    max_width = int(w * 0.85)
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        bbox_test = draw.textbbox((0, 0), test, font=font)
        if bbox_test[2] - bbox_test[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    line_h = draw.textbbox((0, 0), "가", font=font)[3]
    line_gap = 10
    total_text_h = len(lines) * line_h + (len(lines) - 1) * line_gap
    ty_start = int(h * 0.28) - total_text_h // 2  # 상단 30% 영역

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        ty = ty_start + i * (line_h + line_gap)

        # 블러 효과 느낌의 소프트 그림자 (여러 겹)
        for offset, alpha in [(6, 60), (4, 100), (2, 140)]:
            draw.text((tx + offset, ty + offset), line, font=font, fill=(0, 0, 0, alpha))

        # 메인 텍스트 (밝은 흰색)
        draw.text((tx, ty), line, font=font, fill=(255, 255, 255, 255))

    return img.convert("RGB")


def draw_location_badge(img: Image.Image, name: str, location: str) -> Image.Image:
    """좌측 상단(11시 방향)에 가게 이름 + 위치 뱃지 추가"""
    img = img.convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ]
    font_name = None
    font_loc = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_name = ImageFont.truetype(fp, size=48)
                font_loc  = ImageFont.truetype(fp, size=36)
                break
            except Exception:
                continue
    if font_name is None:
        font_name = font_loc = ImageFont.load_default()

    pad_x, pad_y, line_gap = 28, 20, 10
    margin = int(w * 0.05)
    badge_x = margin
    badge_y = int(h * 0.07)

    b_name = draw.textbbox((0, 0), name, font=font_name)
    b_loc  = draw.textbbox((0, 0), location, font=font_loc)
    name_w, name_h = b_name[2] - b_name[0], b_name[3] - b_name[1]
    loc_w,  loc_h  = b_loc[2]  - b_loc[0],  b_loc[3]  - b_loc[1]

    badge_w = max(name_w, loc_w) + pad_x * 2
    badge_h = name_h + line_gap + loc_h + pad_y * 2

    # 반투명 배경 박스
    badge_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_layer)
    badge_draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
        radius=16,
        fill=(0, 0, 0, 160)
    )
    img = Image.alpha_composite(img, badge_layer)
    draw = ImageDraw.Draw(img)

    # 왼쪽 빨간 세로줄
    bar_w = 6
    bar_margin = 16
    bar_x = badge_x + pad_x
    bar_y1 = badge_y + pad_y
    bar_y2 = badge_y + badge_h - pad_y
    draw.rectangle([(bar_x, bar_y1), (bar_x + bar_w, bar_y2)], fill=(220, 40, 40, 255))

    # 가게 이름 (크게) — 빨간 줄 오른쪽
    tx = bar_x + bar_w + bar_margin
    ty = badge_y + pad_y
    draw.text((tx, ty), name, font=font_name, fill=(255, 255, 255, 255))

    # 위치 (작게, 살짝 회색)
    ty2 = ty + name_h + line_gap
    draw.text((tx, ty2), location, font=font_loc, fill=(210, 210, 210, 255))

    return img.convert("RGB")


def get_photos() -> list[str]:
    exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    photos = []
    for ext in exts:
        photos.extend(glob.glob(os.path.join(PHOTOS_DIR, ext)))
    photos.sort()
    return photos


def make_reels(name: str, location: str, price: str, review: str,
               analysis: str, photos: list[str]):
    print("✍️  자막 생성 중...")
    captions = generate_captions(name, location, price, review, analysis, photos)

    print("\n📝 생성된 자막:")
    for i, (p, c) in enumerate(zip(photos, captions)):
        print(f"   {i+1}. {os.path.basename(p)} → {c}")

    confirm = input("\n이 자막으로 영상을 만들까요? (y/n): ").strip().lower()
    if confirm != "y":
        print("취소되었습니다.")
        return

    print("\n🎨 프레임 합성 중...")
    frames = []
    fps = 24
    hold_frames = int(PHOTO_DURATION * fps)

    for photo_path, caption in zip(photos, captions):
        img = ImageOps.exif_transpose(Image.open(photo_path))
        img = fit_image(img, REELS_W, REELS_H)
        img = draw_caption(img, caption)
        img = draw_location_badge(img, name, location)
        frame = np.array(img)
        for _ in range(hold_frames):
            frames.append(frame)

    print("🎬 영상 생성 중...")
    clip = ImageSequenceClip(frames, fps=fps)
    total_duration = clip.duration

    bgm_files = glob.glob(os.path.join(BGM_DIR, "*.mp3"))
    if bgm_files:
        bgm_path = random.choice(bgm_files)
        print(f"🎵 BGM: {os.path.basename(bgm_path)}")
        audio = AudioFileClip(bgm_path)
        if audio.duration < total_duration:
            from moviepy import concatenate_audioclips
            loops = int(total_duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclipped(0, total_duration).with_volume_scaled(BGM_VOLUME)
        clip = clip.with_audio(audio)

    safe_name = name.replace(" ", "_")
    output_path = os.path.join(OUTPUT_DIR, f"{safe_name}_reels.mp4")
    clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac",
                         ffmpeg_params=["-crf", "18", "-preset", "slow"], logger=None)

    print(f"\n✅ 완료! 저장 위치: {output_path}")


if __name__ == "__main__":
    print("=" * 40)
    print("    맛집 릴스 자동 생성기")
    print("=" * 40)
    print()

    # 사진 불러오기
    photos = get_photos()
    if not photos:
        print(f"❌ {PHOTOS_DIR} 에 사진이 없습니다.")
        sys.exit(1)
    print(f"📸 사진 {len(photos)}장 발견\n")

    # 사진 분석
    print("🔍 Claude가 사진을 분석 중...")
    analysis = analyze_photos(photos)
    print("\n" + "=" * 40)
    print("📊 사진 분석 결과")
    print("=" * 40)
    print(analysis)
    print("=" * 40)

    # 사진 순서 확인
    print("\n현재 사진 순서:")
    for i, p in enumerate(photos):
        print(f"  {i+1}. {os.path.basename(p)}")
    reorder = input("\n순서를 바꾸고 싶으면 번호를 입력하세요 (예: 3 1 2 4 5...), 그대로면 엔터: ").strip()
    if reorder:
        try:
            order = [int(x) - 1 for x in reorder.split()]
            photos = [photos[i] for i in order if 0 <= i < len(photos)]
        except Exception:
            print("순서 입력 오류, 기존 순서로 진행합니다.")

    # 맛집 정보 입력
    print()
    name     = input("맛집 이름: ").strip()
    location = input("위치 (예: 서울 홍대): ").strip()
    price    = input("가격대 (예: 1인 15,000원): ").strip()
    review   = input("한 줄 총평 (예: 국물이 진하고 면이 쫄깃함): ").strip()

    print()
    make_reels(name, location, price, review, analysis, photos)
