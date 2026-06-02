#!/usr/bin/env bash
###############################################################################
#  نصب‌کنندهٔ تک‌خطی بازی «جدول کلمات فارسی»  روی سرور اوبونتو
#  اجرا:
#     curl -fsSL <URL>/install.sh | sudo bash
#  یا پس از کپی پروژه:
#     sudo bash install.sh
###############################################################################
set -euo pipefail

# ---------- پیکربندی ----------
APP_NAME="jadval"
APP_DIR="/opt/${APP_NAME}"
HOST="0.0.0.0"
PORT="65535"                       # بیشترین پورت مجاز TCP (به‌جای ۶۵۶۵۶ نامعتبر)
PUBLIC_IP="45.156.186.227"
SERVICE="/etc/systemd/system/${APP_NAME}.service"
PY="python3"

GREEN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say(){ echo -e "${GREEN}▶ $*${NC}"; }
warn(){ echo -e "${YEL}! $*${NC}"; }

if [[ $EUID -ne 0 ]]; then
  echo -e "${RED}این اسکریپت باید با دسترسی root اجرا شود. از: sudo bash install.sh استفاده کنید.${NC}"; exit 1
fi

say "۱) به‌روزرسانی فهرست بسته‌ها و نصب پیش‌نیازها…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl ufw

say "۲) آماده‌سازی پوشهٔ برنامه در ${APP_DIR}…"
mkdir -p "${APP_DIR}"
# اگر اسکریپت از داخل پوشهٔ پروژه اجرا شود، فایل‌ها را کپی کن
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "${SRC_DIR}/app/server.py" ]]; then
  cp -r "${SRC_DIR}/." "${APP_DIR}/"
else
  warn "فایل‌های پروژه در کنار اسکریپت یافت نشد. فرض می‌شود فایل‌ها از قبل در ${APP_DIR} هستند."
fi

say "۳) ساخت محیط مجازی پایتون و نصب وابستگی‌ها…"
cd "${APP_DIR}"
${PY} -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

say "۴) ساخت آیکون‌های PWA (در صورت نبود)…"
if [[ ! -f static/icon-512.png ]]; then
  python - <<'PYEOF'
from PIL import Image, ImageDraw
def mk(sz,p):
    img=Image.new('RGB',(sz,sz),'#0f2a30');d=ImageDraw.Draw(img)
    for i in range(sz):
        t=i/sz;r=int(0x0c+(0x14-0x0c)*t);g=int(0x22+(0x42-0x22)*t);b=int(0x27+(0x4b-0x27)*t)
        d.line([(0,i),(sz,i)],fill=(r,g,b))
    m=sz//12;d.rounded_rectangle([m,m,sz-m,sz-m],radius=sz//8,outline='#e9b949',width=max(2,sz//40))
    cx,cy=sz//2,sz//2;s=sz//4
    d.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)],outline='#3fd6c2',width=max(2,sz//50))
    d.polygon([(cx,cy-s//2),(cx+s//2,cy),(cx,cy+s//2),(cx-s//2,cy)],fill='#e9b949')
    img.save(p)
mk(192,'static/icon-192.png');mk(512,'static/icon-512.png')
PYEOF
fi

say "۵) ساخت سرویس systemd برای اجرای دائمی…"
SECRET_KEY="$(python - <<'PYEOF'
import secrets;print(secrets.token_hex(32))
PYEOF
)"
cat > "${SERVICE}" <<EOF
[Unit]
Description=Jadval - Persian Crossword Game
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
Environment=PORT=${PORT}
Environment=SECRET_KEY=${SECRET_KEY}
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 3 --bind ${HOST}:${PORT} app.server:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

say "۶) باز کردن پورت ${PORT} در فایروال…"
if command -v ufw >/dev/null 2>&1; then
  ufw allow ${PORT}/tcp || true
fi

say "۷) فعال‌سازی و اجرای سرویس…"
systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}
sleep 2

if systemctl is-active --quiet ${APP_NAME}; then
  echo
  echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  ✅ نصب با موفقیت انجام شد!${NC}"
  echo -e "${GREEN}  🎮 بازی در آدرس زیر در دسترس است:${NC}"
  echo -e "${GREEN}     http://${PUBLIC_IP}:${PORT}${NC}"
  echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
  echo "  دستورات مفید:"
  echo "    وضعیت :  systemctl status ${APP_NAME}"
  echo "    لاگ‌ها :  journalctl -u ${APP_NAME} -f"
  echo "    ری‌استارت: systemctl restart ${APP_NAME}"
else
  echo -e "${RED}✗ سرویس اجرا نشد. لاگ را ببینید: journalctl -u ${APP_NAME} -e${NC}"
  exit 1
fi
