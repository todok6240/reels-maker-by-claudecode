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
from database import init_db, save_restaurant, save_reel, save_captions
from PIL import Image, ImageDraw, ImageFont, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass
from moviepy import ImageSequenceClip, AudioFileClip, concatenate_videoclips
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
    """이미지를 분석용으로 축소 후 base64 인코딩 (최대 1280px, 5MB 이하)
    동영상 파일은 첫 프레임을 추출해서 인코딩"""
    import io
    ext = os.path.splitext(photo_path)[1].lower()
    video_exts = {".mp4", ".mov", ".avi", ".m4v", ".mkv", ".3gp"}
    if ext in video_exts:
        from moviepy import VideoFileClip
        clip = VideoFileClip(photo_path)
        frame = clip.get_frame(0)
        clip.close()
        img = Image.fromarray(frame).convert("RGB")
    else:
        img = Image.open(photo_path).convert("RGB")
    max_size = 1280
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
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


CAPTION_PROMPTS = {
    "food": {
        "intro": "맛집/카페 인스타그램 릴스용 자막",
        "info_label": "맛집 정보",
        "fields": lambda n, l, p, r: f"- 가게 이름: {n}\n- 위치: {l}\n- 가격대: {p}\n- 총평: {r}",
        "rules": (
            "- 1번째 사진: \"{location} {name}\" 형태로 위치+이름 소개\n"
            "- 중간 사진들: 음식 맛·식감·분위기를 친근하게 묘사\n"
            "- 마지막 사진: 가격대 언급 + 방문 추천 마무리\n"
            "- 말투 예시: \"뼈 육수가 진하고 고소해요\", \"밥 말아 먹기에 딱이에요\""
        ),
    },
    "travel": {
        "intro": "여행/관광지 인스타그램 릴스용 자막",
        "info_label": "장소 정보",
        "fields": lambda n, l, p, r: f"- 장소명: {n}\n- 위치: {l}\n- 입장료: {p}\n- 총평: {r}",
        "rules": (
            "- 1번째 사진: \"{location} {name}\" 형태로 위치+장소명 소개\n"
            "- 중간 사진들: 풍경·분위기·볼거리를 생생하게 묘사\n"
            "- 마지막 사진: 방문 팁 또는 추천 마무리\n"
            "- 말투 예시: \"뷰가 정말 압도적이에요\", \"꼭 한번 와보세요\""
        ),
    },
    "product": {
        "intro": "상품 리뷰 인스타그램 릴스용 자막",
        "info_label": "상품 정보",
        "fields": lambda n, l, p, r: f"- 상품명: {n}\n- 구매처: {l}\n- 가격: {p}\n- 총평: {r}",
        "rules": (
            "- 1번째 사진: 상품명 + 한 줄 소개\n"
            "- 중간 사진들: 디자인·기능·사용감을 솔직하게 묘사\n"
            "- 마지막 사진: 가격 언급 + 추천 여부 마무리\n"
            "- 말투 예시: \"마감이 생각보다 깔끔해요\", \"가성비 진짜 좋아요\""
        ),
    },
    "fitness": {
        "intro": "운동/헬스 인스타그램 릴스용 자막",
        "info_label": "운동 정보",
        "fields": lambda n, l, p, r: f"- 운동 종목/장소: {n}\n- 위치: {l}\n- 이용 요금: {p}\n- 총평: {r}",
        "rules": (
            "- 1번째 사진: 운동 종목 + 장소 소개\n"
            "- 중간 사진들: 운동 강도·시설·분위기를 생생하게 묘사\n"
            "- 마지막 사진: 요금 언급 + 추천 마무리\n"
            "- 말투 예시: \"코치님이 정말 꼼꼼하게 봐줘요\", \"땀이 엄청나요\""
        ),
    },
    "vlog": {
        "intro": "일상/브이로그 인스타그램 릴스용 자막",
        "info_label": "브이로그 정보",
        "fields": lambda n, l, p, r: f"- 제목: {n}\n- 장소: {l}\n- 내용 요약: {r}",
        "rules": (
            "- 1번째 사진: 브이로그 제목 또는 날짜·장소 소개\n"
            "- 중간 사진들: 순간순간의 감정·경험을 감성적으로 묘사\n"
            "- 마지막 사진: 여운 남기는 한 줄 마무리\n"
            "- 말투 예시: \"오늘 하루 진짜 행복했어요\", \"또 오고 싶은 곳이에요\""
        ),
    },
}


def generate_captions(name: str, location: str, price: str, review: str,
                      analysis: str, photo_order: list[str],
                      content_type: str = "food") -> list[str]:
    """Claude API로 자막 생성"""
    client = anthropic.Anthropic(api_key=get_api_key())

    photo_count = len(photo_order)
    filenames = "\n".join([f"{i+1}. {os.path.basename(p)}" for i, p in enumerate(photo_order)])

    cfg = CAPTION_PROMPTS.get(content_type, CAPTION_PROMPTS["food"])
    info_str = cfg["fields"](name, location, price, review)
    rules_str = cfg["rules"].format(name=name, location=location)

    prompt = f"""{cfg["intro"]} 자막을 {photo_count}개 만들어줘.

{cfg["info_label"]}:
{info_str}

사진 분석 결과:
{analysis}

사진 순서 ({photo_count}장):
{filenames}

자막 구성 규칙:
{rules_str}

조건:
- 번호나 따옴표 없이 자막만 한 줄씩
- 정확히 {photo_count}줄
- 한국어
- 이모티콘, 특수문자 절대 사용 금지 (텍스트만)
- 각 자막은 반드시 18자 이내 (공백 제외)
- 말투: 해요체 (있어요, 좋아요, 맛있어요) — 딱딱한 명사형 종결 금지
- 가격은 반드시 숫자+콤마 형식으로 표기 (예: 12,000원) — 한글 숫자 금지"""

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
        "/Users/hongjuhyeong/Library/Fonts/esamanru OTF Bold.otf",  # 이사만루체
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
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
        "/Users/hongjuhyeong/Library/Fonts/esamanru OTF Bold.otf",  # 이사만루체
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


VIDEO_EXTS = {".mp4", ".mov", ".avi", ".m4v", ".mkv", ".3gp"}

def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS



VIDEO_FPS    = 30  # 동영상 슬라이드쇼 프레임레이트 (1초당 30프레임 추출)


def extract_video_frames(video_path: str, num_frames: int = None) -> list:
    """동영상에서 균등 간격으로 프레임을 추출해 PIL Image 리스트로 반환
    num_frames 미지정 시 VIDEO_FPS * PHOTO_DURATION 만큼 추출 (30fps 기준)"""
    if num_frames is None:
        num_frames = int(VIDEO_FPS * PHOTO_DURATION)  # 기본 90프레임
    from moviepy import VideoFileClip as _VFC
    clip = _VFC(video_path)
    duration = clip.duration
    times = [min(duration * i / num_frames, duration - 0.05) for i in range(num_frames)]
    frames = [Image.fromarray(clip.get_frame(t)).convert("RGB") for t in times]
    clip.close()
    return frames


def get_photos() -> list[str]:
    exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    photos = []
    for ext in exts:
        photos.extend(glob.glob(os.path.join(PHOTOS_DIR, ext)))
    photos.sort()
    return photos


def make_reels(name: str, location: str, price: str, review: str,
               analysis: str, photos: list[str], captions: list[str] = None,
               output_dir: str = None):
    if captions is None:
        print("✍️  자막 생성 중...")
        captions = generate_captions(name, location, price, review, analysis, photos)

        print("\n📝 생성된 자막:")
        for i, (p, c) in enumerate(zip(photos, captions)):
            print(f"   {i+1}. {os.path.basename(p)} → {c}")

        confirm = input("\n이 자막으로 영상을 만들까요? (y/n): ").strip().lower()
        if confirm != "y":
            print("취소되었습니다.")
            return

    import logging
    import time

    TIMEOUT_SEC = 300  # 5분 초과 시 타임아웃

    print("\n🎨 프레임 합성 중...")
    fps = VIDEO_FPS  # 30fps
    hold_frames = int(PHOTO_DURATION * fps)  # 사진: 90프레임 = 3초

    # 사진/동영상 혼합 처리
    segments = []
    video_frame_count = int(VIDEO_FPS * PHOTO_DURATION)  # 동영상: 90프레임 추출, 각 1장씩
    for i, (media_path, caption) in enumerate(zip(photos, captions)):
        logging.info("[%d/%d] 처리 중: %s", i + 1, len(photos), os.path.basename(media_path))
        if is_video(media_path):
            # 동영상 → 30fps×3초 = 90프레임 추출, 각 프레임 1장씩 (총 3초)
            pil_frames = extract_video_frames(media_path, video_frame_count)
            seq = [np.array(
                draw_location_badge(draw_caption(fit_image(pf, REELS_W, REELS_H), caption), name, location)
            ) for pf in pil_frames]
            seg = ImageSequenceClip(seq, fps=fps)
        else:
            img = ImageOps.exif_transpose(Image.open(media_path))
            img = fit_image(img, REELS_W, REELS_H)
            img = draw_caption(img, caption)
            img = draw_location_badge(img, name, location)
            frame_arr = np.array(img)
            seg = ImageSequenceClip([frame_arr] * hold_frames, fps=fps)
        segments.append(seg)

    print("🎬 영상 인코딩 중... (약 30초~2분 소요)")
    logging.info("concatenate_videoclips 시작 (클립 %d개)", len(segments))
    t0 = time.time()
    clip = concatenate_videoclips(segments, method="chain")
    logging.info("concatenate 완료 (%.1fs)", time.time() - t0)
    total_duration = clip.duration

    bgm_files = glob.glob(os.path.join(BGM_DIR, "*.mp3"))
    if bgm_files:
        bgm_path = random.choice(bgm_files)
        logging.info("BGM 선택 (%d개 중): %s", len(bgm_files), os.path.basename(bgm_path))
        print(f"🎵 BGM ({len(bgm_files)}개 중 랜덤): {os.path.basename(bgm_path)}")
        audio = AudioFileClip(bgm_path)
        if audio.duration < total_duration:
            from moviepy import concatenate_audioclips
            loops = int(total_duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * loops)
        audio = audio.subclipped(0, total_duration).with_volume_scaled(BGM_VOLUME)
        clip = clip.with_audio(audio)

    safe_name = name.replace(" ", "_")
    out_dir = output_dir if output_dir else OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f"{safe_name}_reels.mp4")

    logging.info("write_videofile 시작: %s", output_path)
    t1 = time.time()

    import threading as _threading
    encode_error = [None]
    encode_done  = [False]

    def _encode():
        try:
            clip.write_videofile(
                output_path, fps=fps, codec="libx264", audio_codec="aac",
                ffmpeg_params=["-crf", "23", "-preset", "fast"],
                logger=None
            )
            encode_done[0] = True
        except Exception as e:
            encode_error[0] = e

    enc_thread = _threading.Thread(target=_encode, daemon=True)
    enc_thread.start()
    enc_thread.join(timeout=TIMEOUT_SEC)

    if enc_thread.is_alive():
        elapsed = time.time() - t1
        raise TimeoutError(f"영상 인코딩 {TIMEOUT_SEC}초 초과 (경과: {elapsed:.0f}s). "
                           "파일 수를 줄이거나 동영상 해상도를 낮춰주세요.")
    if encode_error[0]:
        raise encode_error[0]

    logging.info("write_videofile 완료 (%.1fs)", time.time() - t1)

    print(f"\n✅ 완료! 저장 위치: {output_path}")
    return output_path

    # CLI 실행 시에만 DB 직접 저장 (웹은 app.py에서 처리)
    if output_dir is None:
        restaurant_id = save_restaurant("cli", name, location, price, review)
        reel_id = save_reel(restaurant_id, output_path, len(photos))
        save_captions(reel_id, photos, captions)
        print("💾 DB 저장 완료")


if __name__ == "__main__":
    print("=" * 40)
    print("    맛집 릴스 자동 생성기")
    print("=" * 40)
    print()

    init_db()

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
