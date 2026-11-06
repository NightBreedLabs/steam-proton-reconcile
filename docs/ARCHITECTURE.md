# steam-proton-reconcile Architecture

## The Problem

On Linux distributions (particularly Bazzite, SteamOS, Fedora Silverblue, and gaming-oriented desktop environments), users frequently install multiple Proton versions using tool managers such as **ProtonPlus** or **ProtonUp-Qt**.

Two distinct issues prevent Steam from seeing these tools:

1. **Manifest Tool Key Collisions**:
   Managers like ProtonPlus rewrite `compatibilitytool.vdf` for rolling "Latest" releases with a generic key (e.g. `"Proton-CachyOS Latest"`). When a user installs both the baseline `x86_64` variant and the optimized `x86_64_v3` variant, both directories contain the exact same internal key under `compat_tools`. Steam's VDF parser drops the duplicate:
   ```text
   Skipping duplicate entry 0 Proton-CachyOS Latest in m_vecPendingToolRegistered
   ```

2. **Launcher Tool Partitioning**:
   ProtonPlus segregates installations into separate directories based on the selected launcher tab (e.g., `~/.local/share/Steam/compatibilitytools.d` vs `~/.config/heroic/tools/proton`). Steam does not search Heroic's directory.

3. **Steam Startup Lifecycle**:
   Steam scans `compatibilitytools.d` strictly at process startup. When running in the background as a user service or system tray icon, newly downloaded Proton runners remain invisible until Steam is restarted.

---

## How It Works

```
   ProtonPlus / ProtonUp-Qt / Heroic / Manual Extraction
                         │
                         ▼
        ┌───────────────────────────────────┐
        │ ~/.local/share/Steam/compat...    │
        │ ~/.config/heroic/tools/proton...  │
        └─────────────────┬─────────────────┘
                          │ (inotify event)
                          ▼
             steam-proton-reconcile.path
                          │
                          ▼
            steam-proton-reconcile.service
                          │
                          ▼
            steam-proton-reconcile CLI
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
 1. Fix Manifests                     2. Sync Runners
    (Deduplicate VDF tool keys            (Symlink Heroic tools
     and clear display names)              into Steam)
       │                                     │
       └──────────────────┬──────────────────┘
                          │
                          ▼
                3. Lifecycle Check
                (Is a game running?)
               ├── Yes ──► Send desktop notification (restart deferred)
               └── No  ──► Prompt or graceful restart of app-steam@autostart
```

---

## Key Advantages

* **Pure Standard Library**: Zero external dependencies (only standard Python 3.8+).
* **Zero Idle Footprint**: Managed by `systemd.path`, waking only on filesystem modifications.
* **Game-Safe**: Detects active wine processes (`wineserver` / `proton waitforexitandrun`) before initiating any restart.
* **Preserves Mappings**: Maintains backward compatibility with existing shortcuts and game mappings.
