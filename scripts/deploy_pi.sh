#!/usr/bin/env bash
set -euo pipefail

PI_HOST="${PI_HOST:-192.168.1.5}"
PI_USER="${PI_USER:-pi}"
PI_PATH="${PI_PATH:-/home/pi/shiftFM-web}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if command -v sshpass >/dev/null 2>&1 && [[ -n "${PI_PASS:-}" ]]; then
  SCP_CMD=(sshpass -p "${PI_PASS}" scp -o StrictHostKeyChecking=no)
  SSH_CMD=(sshpass -p "${PI_PASS}" ssh -o StrictHostKeyChecking=no)
else
  SCP_CMD=(scp)
  SSH_CMD=(ssh)
fi

echo "Deploying to ${PI_USER}@${PI_HOST}:${PI_PATH}"
${SCP_CMD[@]} "${ROOT_DIR}/server.py" "${ROOT_DIR}/config.json" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
${SCP_CMD[@]} "${ROOT_DIR}/static/index.html" "${ROOT_DIR}/static/app.css" "${ROOT_DIR}/static/app.js" "${PI_USER}@${PI_HOST}:${PI_PATH}/static/"

${SSH_CMD[@]} "${PI_USER}@${PI_HOST}" "pkill -f '^python3 ${PI_PATH}/server.py' || true; nohup python3 ${PI_PATH}/server.py > ${PI_PATH}/server.log 2>&1 &"
echo "Done."
