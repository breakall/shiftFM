#!/usr/bin/env bash
set -euo pipefail

PI_USER="${PI_USER:-pi}"
INSTALL_DIR="${INSTALL_DIR:-/home/pi/shiftFM-web}"
RSS_PORT="${RSS_PORT:-8088}"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo: sudo -E ./scripts/install_pi.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/server.py" ]]; then
  ROOT_DIR="${SCRIPT_DIR}"
else
  ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi

echo "Installing dependencies..."
apt-get update -y
apt-get install -y rtl-sdr ffmpeg lighttpd

echo "Preparing directories..."
mkdir -p "${INSTALL_DIR}/recordings" "${INSTALL_DIR}/static" "/var/log/shiftfm-lighttpd"
chown -R "${PI_USER}:${PI_USER}" "${INSTALL_DIR}"
chown -R www-data:www-data "/var/log/shiftfm-lighttpd"

echo "Copying application files..."
if [[ "${ROOT_DIR}" != "${INSTALL_DIR}" ]]; then
  cp "${ROOT_DIR}/server.py" "${INSTALL_DIR}/"
  cp "${ROOT_DIR}/static/index.html" "${ROOT_DIR}/static/app.css" "${ROOT_DIR}/static/app.js" "${INSTALL_DIR}/static/"
fi

if [[ -f "${ROOT_DIR}/config.json" && "${ROOT_DIR}" != "${INSTALL_DIR}" ]]; then
  cp "${ROOT_DIR}/config.json" "${INSTALL_DIR}/"
elif [[ ! -f "${INSTALL_DIR}/config.json" ]]; then
  cat > "${INSTALL_DIR}/config.json" <<EOF
{
  "base_url": "http://localhost:${RSS_PORT}",
  "rss_description": "Time-shifted FM recordings",
  "rss_title": "shiftFM"
}
EOF
fi

if [[ ! -f "${INSTALL_DIR}/schedules.json" ]]; then
  cat > "${INSTALL_DIR}/schedules.json" <<EOF
{
  "schedules": []
}
EOF
fi

echo "Installing lighttpd config..."
LIGHTTPD_SOURCE="${ROOT_DIR}/lighttpd/shiftfm.conf"
if [[ ! -f "${LIGHTTPD_SOURCE}" ]]; then
  LIGHTTPD_SOURCE="${ROOT_DIR}/shiftfm.conf"
fi
sed "s/server.port = 8088/server.port = ${RSS_PORT}/" "${LIGHTTPD_SOURCE}" > /etc/lighttpd/shiftfm.conf

echo "Installing systemd services..."
SHIFT_SERVICE="${ROOT_DIR}/systemd/shiftfm.service"
LIGHTTPD_SERVICE="${ROOT_DIR}/systemd/shiftfm-lighttpd.service"
if [[ ! -f "${SHIFT_SERVICE}" ]]; then
  SHIFT_SERVICE="${ROOT_DIR}/shiftfm.service"
fi
if [[ ! -f "${LIGHTTPD_SERVICE}" ]]; then
  LIGHTTPD_SERVICE="${ROOT_DIR}/shiftfm-lighttpd.service"
fi
sed "s/User=pi/User=${PI_USER}/" "${SHIFT_SERVICE}" \
  | sed "s#/home/pi/shiftFM-web#${INSTALL_DIR}#g" \
  > /etc/systemd/system/shiftfm.service
cp "${LIGHTTPD_SERVICE}" /etc/systemd/system/shiftfm-lighttpd.service

systemctl daemon-reload
systemctl enable --now shiftfm.service shiftfm-lighttpd.service

echo "Install complete."
echo "UI:  http://<pi-ip>:8000"
echo "RSS: http://<pi-ip>:${RSS_PORT}/rss.xml"
