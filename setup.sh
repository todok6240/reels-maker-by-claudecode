#!/bin/bash
# =============================================================
# Reels Maker 서버 초기 세팅 스크립트
# 사용법: bash setup.sh
# =============================================================
set -e

REPO="todok6240/reels-maker-by-claudecode"
APP_DIR="/root/reels-maker-by-claudecode"
SERVICE_NAME="rsmaker"

echo "▶ 패키지 업데이트"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv ffmpeg nginx redis-server git curl

echo "▶ 로그 디렉터리 생성"
mkdir -p /var/log/rsmaker

echo "▶ 레포 클론"
if [ -d "$APP_DIR" ]; then
    echo "  이미 존재 → git pull"
    cd "$APP_DIR" && git pull origin master
else
    git clone "https://github.com/$REPO.git" "$APP_DIR"
fi
cd "$APP_DIR"

echo "▶ Python 가상환경 및 패키지 설치"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "▶ 데이터 디렉터리 생성"
mkdir -p photos output

echo "▶ .env 파일 확인"
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. 아래 내용을 채워서 .env 파일을 생성하세요:"
    cat <<'EOF'
ANTHROPIC_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FLASK_SECRET_KEY=
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
EOF
    exit 1
fi

echo "▶ Redis 활성화"
systemctl enable redis-server
systemctl start redis-server

echo "▶ systemd 서비스 등록"
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Reels Maker Flask App
After=network.target redis-server.service

[Service]
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/gunicorn -c ${APP_DIR}/gunicorn.conf.py app:app
Restart=always
RestartSec=5
EnvironmentFile=${APP_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

echo "▶ Nginx 설정"
cp "${APP_DIR}/nginx.conf" /etc/nginx/sites-available/rsmaker
ln -sf /etc/nginx/sites-available/rsmaker /etc/nginx/sites-enabled/rsmaker
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "✅ 완료! http://49.50.131.80 에서 확인하세요."
