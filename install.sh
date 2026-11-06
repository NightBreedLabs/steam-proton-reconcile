#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="${HOME}/.local/bin/steam-proton-reconcile"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "=== Installing steam-proton-reconcile ==="

# 1. Install CLI script
mkdir -p "${HOME}/.local/bin"
cp -f "${SCRIPT_DIR}/steam_proton_reconcile.py" "${BIN_DEST}"
chmod +x "${BIN_DEST}"
echo "✓ Installed ${BIN_DEST}"

# 2. Install systemd user path and service units
mkdir -p "${SYSTEMD_USER_DIR}"
cp -f "${SCRIPT_DIR}/systemd/steam-proton-reconcile.path" "${SYSTEMD_USER_DIR}/"
cp -f "${SCRIPT_DIR}/systemd/steam-proton-reconcile.service" "${SYSTEMD_USER_DIR}/"
echo "✓ Installed systemd units to ${SYSTEMD_USER_DIR}"

# 3. Reload systemd and enable path watcher
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    if systemctl --user is-active --quiet graphical-session.target 2>/dev/null; then
        systemctl --user enable --now steam-proton-reconcile.path
        echo "✓ Enabled and started steam-proton-reconcile.path"
    else
        systemctl --user enable steam-proton-reconcile.path
        echo "✓ Enabled steam-proton-reconcile.path (will start with graphical session)"
    fi
fi

# 4. Run an initial check and reconciliation
echo "=== Running initial reconciliation ==="
"${BIN_DEST}" --apply

echo ""
echo "Installation complete!"
