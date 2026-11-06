# steam-proton-reconcile

> **Automatic Proton compatibility tool deduplication, Heroic cross-synchronization, and Steam lifecycle manager for Linux gaming.**

[![Unit Tests](https://github.com/NightBreedLabs/steam-proton-reconcile/actions/workflows/test.yml/badge.svg)](https://github.com/NightBreedLabs/steam-proton-reconcile/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`steam-proton-reconcile` automatically detects, resolves, and repairs Proton compatibility tool issues on Linux (Bazzite, SteamOS, Fedora Silverblue, Arch, and standard desktop distributions).

---

## The Problem

When managing Proton runners using **ProtonPlus**, **ProtonUp-Qt**, or manual extraction:
1. **Silent Manifest Dropping**: Installing multiple architecture variants (e.g. `x86_64` baseline alongside `x86_64_v3` optimized builds) writes identical internal keys (`"Proton-CachyOS Latest"`) to `compatibilitytool.vdf`. Steam silently rejects one with `Skipping duplicate entry in m_vecPendingToolRegistered`.
2. **Heroic / Steam Siloing**: Runners installed under Heroic Games Launcher (`~/.config/heroic/tools/proton/`) are not indexed by Steam without symlinks.
3. **Steam Background Lifecycle**: Steam only scans compatibility tools on initial startup. When running in the background as a systemd user service or tray app, new runners remain invisible until Steam is fully restarted.

---

## Features

* **Manifest Collision Deduplication**: Scans `compatibilitytools.d/`, detects duplicate internal VDF keys, and disambiguates them using `.protonplus` metadata and directory architecture tags.
* **Heroic Cross-Synchronization**: Automatically links Heroic Proton runners into Steam while avoiding redundant duplicate keys.
* **Game-Safe Lifecycle Management**: Checks for active Wine/Proton processes before attempting a Steam restart.
* **Zero-Overhead Automation**: Ships with native `systemd.path` units watching filesystem inotify events with 0% idle CPU and 0 MB RAM overhead.
* **Zero Dependencies**: Pure Python 3 standard library (`/usr/bin/python3`).

---

## Installation

```bash
git clone https://github.com/NightBreedLabs/steam-proton-reconcile.git
cd steam-proton-reconcile
./install.sh
```

The installer:
1. Installs the CLI executable to `~/.local/bin/steam-proton-reconcile`.
2. Copies systemd user units to `~/.config/systemd/user/`.
3. Enables and starts the `steam-proton-reconcile.path` inotify watcher.
4. Performs an initial check and reconciliation.

---

## Usage

### CLI Commands

```bash
# Check status and audit manifests without applying changes (dry-run)
steam-proton-reconcile --check

# Apply manifest deduplication and cross-link Heroic tools
steam-proton-reconcile --apply

# Apply changes and restart Steam if no games are running
steam-proton-reconcile --apply --restart

# Apply changes and send a desktop notification via notify-send
steam-proton-reconcile --apply --notify
```

---

## Architecture & How It Works

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for full technical design details, data flow diagrams, and upstream patch recommendations for ProtonPlus and Bazzite.

---

## Uninstallation

```bash
cd steam-proton-reconcile
./uninstall.sh
```

---

## License

MIT License. Copyright (c) 2026 [NightBreedLabs](https://github.com/NightBreedLabs).
