#!/usr/bin/env bash
###############################################################################
#  نصب‌کنندهٔ تک‌خطی پلتفرم «سازه‌مارکت» روی سرور اوبونتو
#  اجرا (بدون نیاز به کلون دستی؛ خودش سورس را از گیت‌هاب می‌گیرد):
#     curl -fsSL https://raw.githubusercontent.com/For256256/Jadval-game/main/install.sh | sudo bash
#  یا پس از کپی/کلون دستی پروژه:
#     sudo bash install.sh
###############################################################################
set -euo pipefail

# ---------- پیکربندی ----------
APP_NAME="sazehmarket"
APP_DIR="/opt/${APP_NAME}"
HOST="0.0.0.0"
PORT="${PORT:-8080}"
SERVICE="/etc/systemd/system/${APP_NAME}.service"
PY="python3"
REPO_URL="${REPO_URL:-https://github.com/For256256/Jadval-game.git}"
BRANCH="${BRANCH:-main}"

GREEN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say(){ echo -e "${GREEN}▶ $*${NC}"; }
warn(){ echo -e "${YEL}! $*${NC}"; }

if [[ $EUID -ne 0 ]]; then
  echo -e "${RED}این اسکریپت باید با دسترسی root اجرا شود. از: sudo bash install.sh استفاده کنید.${NC}"; exit 1
fi

say "۱) به‌روزرسانی فهرست بسته‌ها و نصب پیش‌نیازها…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl ufw

say "۲) آماده‌سازی پوشهٔ برنامه در ${APP_DIR}…"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [[ -f "${SRC_DIR}/app/server.py" ]]; then
  say "استفاده از فایل‌های موجود کنار اسکریپت…"
  mkdir -p "${APP_DIR}"
  cp -r "${SRC_DIR}/." "${APP_DIR}/"
else
  say "دریافت سورس پروژه از ${REPO_URL} (شاخهٔ ${BRANCH})…"
  rm -rf "${APP_DIR}"
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

say "۳) ساخت محیط مجازی پایتون و نصب وابستگی‌ها…"
cd "${APP_DIR}"
${PY} -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

say "۴) ساخت سرویس systemd برای اجرای دائمی…"
SECRET_KEY="$(python - <<'PYEOF'
import secrets;print(secrets.token_hex(32))
PYEOF
)"
cat > "${SERVICE}" <<EOF
[Unit]
Description=SazehMarket - B2B/B2C Construction Materials Marketplace
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

say "۵) باز کردن پورت ${PORT} در فایروال…"
if command -v ufw >/dev/null 2>&1; then
  ufw allow ${PORT}/tcp || true
fi

say "۶) فعال‌سازی و اجرای سرویس…"
systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}
sleep 2

if systemctl is-active --quiet ${APP_NAME}; then
  echo
  echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  ✅ نصب با موفقیت انجام شد!${NC}"
  echo -e "${GREEN}  🏗️  سازه‌مارکت روی پورت زیر در دسترس است:${NC}"
  echo -e "${GREEN}     http://<server-ip>:${PORT}${NC}"
  echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
  echo "  دستورات مفید:"
  echo "    وضعیت :  systemctl status ${APP_NAME}"
  echo "    لاگ‌ها :  journalctl -u ${APP_NAME} -f"
  echo "    ری‌استارت: systemctl restart ${APP_NAME}"
else
  echo -e "${RED}✗ سرویس اجرا نشد. لاگ را ببینید: journalctl -u ${APP_NAME} -e${NC}"
  exit 1
fi
