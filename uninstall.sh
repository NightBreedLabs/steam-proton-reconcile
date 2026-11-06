#!/usr/bin/env bash
set -euo pipefail

BIN_DEST="${HOME}/.local/bin/steam-proton-reconcile"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "=== Uninstalling steam-proton-reconcile ==="

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop steam-proton-reconcile.path 2>/dev/null || true
    systemctl --user disable steam-proton-reconcile.path 2>/dev/null || true
    systemctl --user stop steam-proton-reconcile.service 2>/dev/null || true
fi

rm -f "${SYSTEMD_USER_DIR}/steam-proton-reconcile.path"
rm -f "${SYSTEMD_USER_DIR}/steam-proton-reconcile.service"
rm -f "${BIN_DEST}"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
fi

echo "✓ Removed CLI and systemd units."
echo "Uninstallation complete."
