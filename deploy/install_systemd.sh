#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/opt/legenda}"
SERVICE_NAME="legenda-orchestrator"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root (sudo)." >&2
  exit 1
fi

if ! id legenda >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin legenda
fi

usermod -a -G audio legenda || true
chown -R legenda:audio "$APP_DIR"

sed "s|/opt/legenda|$APP_DIR|g" "$APP_DIR/deploy/legenda-orchestrator.service" > "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl --no-pager status "$SERVICE_NAME"
