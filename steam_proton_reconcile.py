#!/usr/bin/env python3
"""
Steam & Heroic Proton Compatibility Reconciler for Linux (Bazzite / Steam Deck / Desktop).

Copyright (c) 2026 NightBreedLabs.
Licensed under the MIT License.

Features:
1. Manifest Collision Resolution:
   Disambiguates duplicate internal keys and display names in compatibilitytool.vdf
   when multiple architecture variants (e.g. baseline x86_64 vs x86_64_v3) of
   the same Proton release are installed by managers like ProtonPlus or ProtonUp-Qt.

2. Cross-Launcher Synchronization:
   Discovers Proton runners installed into Heroic Games Launcher
   (~/.config/heroic/tools/proton) and safely symlinks them into Steam
   (~/.local/share/Steam/compatibilitytools.d), avoiding redundant duplicates.

3. Live Steam Process Lifecycle Detection:
   Monitors whether Steam is running, checks whether any Wine/Proton games are
   actively in-session, and either performs an automatic graceful restart or
   sends a non-intrusive desktop notification.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Set, Tuple

__version__ = "1.0.0"

DEFAULT_STEAM_COMPAT_DIR = os.path.expanduser("~/.local/share/Steam/compatibilitytools.d")
DEFAULT_HEROIC_PROTON_DIR = os.path.expanduser("~/.config/heroic/tools/proton")


def parse_manifest(vdf_path: str) -> Optional[Dict[str, str]]:
    """Parse key fields from a compatibilitytool.vdf file."""
    if not os.path.isfile(vdf_path):
        return None
    try:
        with open(vdf_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return None

    key_match = re.search(r'"compat_tools"\s*\{\s*"([^"]+)"', content)
    display_match = re.search(r'"display_name"\s*"([^"]+)"', content)

    if not key_match:
        return None

    return {
        "key": key_match.group(1),
        "display_name": display_match.group(1) if display_match else key_match.group(1),
        "content": content,
    }


def write_manifest(vdf_path: str, new_key: str, new_display_name: str) -> bool:
    """Rewrite internal tool key and display_name in a compatibilitytool.vdf file."""
    manifest = parse_manifest(vdf_path)
    if not manifest:
        return False

    old_content = manifest["content"]
    old_key = manifest["key"]

    # Replace the tool key under compat_tools
    pattern_key = re.compile(
        r'("compat_tools"\s*\{\s*")' + re.escape(old_key) + r'(")'
    )
    new_content = pattern_key.sub(r"\g<1>" + new_key + r"\g<2>", old_content, count=1)

    # Replace display_name
    pattern_display = re.compile(r'("display_name"\s*")([^"]*)(")')
    new_content = pattern_display.sub(
        r"\g<1>" + new_display_name + r"\g<3>", new_content, count=1
    )

    if new_content == old_content:
        return True

    try:
        with open(vdf_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except OSError:
        return False


def get_protonplus_meta(dir_path: str) -> Dict[str, str]:
    """Read .protonplus JSON metadata if present."""
    meta_path = os.path.join(dir_path, ".protonplus")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def get_version_info(dir_path: str) -> str:
    """Read version file if present."""
    version_path = os.path.join(dir_path, "version")
    if os.path.isfile(version_path):
        try:
            with open(version_path, "r", encoding="utf-8", errors="replace") as f:
                line = f.readline().strip()
                parts = line.split(None, 1)
                return parts[1] if len(parts) > 1 else line
        except OSError:
            pass
    return ""


def get_existing_steam_keys(steam_dir: str) -> Set[str]:
    """Get the set of existing tool keys registered in steam_dir."""
    keys = set()
    if not os.path.isdir(steam_dir):
        return keys

    for item in os.listdir(steam_dir):
        item_path = os.path.join(steam_dir, item)
        if not (os.path.isdir(item_path) or os.path.islink(item_path)):
            continue
        vdf = os.path.join(item_path, "compatibilitytool.vdf")
        m = parse_manifest(vdf)
        if m:
            keys.add(m["key"])
    return keys


def sync_heroic_to_steam(
    heroic_dir: str = DEFAULT_HEROIC_PROTON_DIR,
    steam_dir: str = DEFAULT_STEAM_COMPAT_DIR,
    dry_run: bool = False,
) -> List[str]:
    """Ensure all Proton runners installed in Heroic are available in Steam."""
    actions = []
    if not os.path.isdir(heroic_dir):
        return actions

    os.makedirs(steam_dir, exist_ok=True)
    existing_steam_keys = get_existing_steam_keys(steam_dir)

    for item in sorted(os.listdir(heroic_dir)):
        heroic_item_path = os.path.join(heroic_dir, item)
        if not (os.path.isdir(heroic_item_path) or os.path.islink(heroic_item_path)):
            continue

        vdf_path = os.path.join(heroic_item_path, "compatibilitytool.vdf")
        manifest = parse_manifest(vdf_path)
        if not manifest:
            continue

        steam_target = os.path.join(steam_dir, item)
        if os.path.exists(steam_target):
            continue

        # If a tool with the exact same internal key is already present in Steam, skip
        if manifest["key"] in existing_steam_keys:
            continue

        actions.append(f"Link Heroic tool '{item}' -> Steam")
        if not dry_run:
            try:
                os.symlink(heroic_item_path, steam_target)
                existing_steam_keys.add(manifest["key"])
            except OSError as e:
                actions.append(f"ERROR: Failed to symlink {item}: {e}")

    return actions


def reconcile_manifests(
    steam_dir: str = DEFAULT_STEAM_COMPAT_DIR,
    dry_run: bool = False,
) -> List[str]:
    """
    Scan compatibility tools in steam_dir, detect collisions, and sanitize manifests.
    """
    actions = []
    if not os.path.isdir(steam_dir):
        return actions

    tools = []
    for item in sorted(os.listdir(steam_dir)):
        item_path = os.path.join(steam_dir, item)
        if not (os.path.isdir(item_path) or os.path.islink(item_path)):
            continue

        vdf_path = os.path.join(item_path, "compatibilitytool.vdf")
        manifest = parse_manifest(vdf_path)
        if not manifest:
            continue

        meta = get_protonplus_meta(item_path)
        version = get_version_info(item_path)
        tools.append({
            "dirname": item,
            "path": item_path,
            "vdf_path": vdf_path,
            "key": manifest["key"],
            "display_name": manifest["display_name"],
            "variant_id": meta.get("variant_id", ""),
            "version": version,
        })

    # Group by key to detect collisions
    key_groups: Dict[str, List[dict]] = {}
    for t in tools:
        key_groups.setdefault(t["key"], []).append(t)

    for key, group in key_groups.items():
        if len(group) > 1:
            actions.append(f"Collision detected for tool key '{key}' across {len(group)} folders:")
            for member in group:
                actions.append(f"  - {member['dirname']} (current display: '{member['display_name']}')")

            # Resolve collision based on directory names and variants
            for member in group:
                dirname = member["dirname"]
                var_id = member["variant_id"]

                # Detect variant architecture
                if "x86_64_v3" in dirname or "x86-64-v3" in var_id:
                    new_key = f"{key}" if "Latest" in key and not any("x86_64" in m["dirname"] and "v3" not in m["dirname"] for m in group) else f"{key}-x86_64_v3"
                    new_display = f"{key} (x86_64_v3)"
                elif "x86_64" in dirname or "x86-64" in var_id:
                    new_key = f"{key}-x86_64"
                    new_display = f"{key} (x86_64)"
                else:
                    new_key = dirname
                    new_display = dirname

                if new_key != member["key"] or new_display != member["display_name"]:
                    actions.append(f"  => Update '{dirname}': key='{new_key}', display='{new_display}'")
                    if not dry_run:
                        if not write_manifest(member["vdf_path"], new_key, new_display):
                            actions.append(f"ERROR: Failed writing manifest for {dirname}")

    return actions


def is_game_running() -> bool:
    """Check if any Wine or Proton game process is currently running."""
    try:
        output = subprocess.check_output(
            ["pgrep", "-f", r"wineserver|proton.*waitforexitandrun"],
            stderr=subprocess.DEVNULL,
        )
        return bool(output.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_steam_running() -> bool:
    """Check if Steam client is actively running."""
    try:
        output = subprocess.check_output(["pgrep", "-x", "steam"], stderr=subprocess.DEVNULL)
        return bool(output.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def restart_steam() -> bool:
    """Restart Steam gracefully via systemd user autostart service or CLI."""
    if is_game_running():
        return False

    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", "app-steam@autostart.service"],
            capture_output=True,
        )
        if res.returncode == 0:
            subprocess.run(["systemctl", "--user", "restart", "app-steam@autostart.service"], check=True)
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    try:
        subprocess.run(["steam", "-shutdown"], capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def notify(title: str, message: str, icon: str = "steam") -> None:
    """Send a user notification via notify-send."""
    try:
        subprocess.run(
            ["notify-send", "-a", "Steam Compatibility", "-i", icon, title, message],
            capture_output=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile and synchronize Steam Proton compatibility tools on Linux."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--check", action="store_true", help="Audit tools and manifests without making changes."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply fixes to manifests and synchronize Heroic tools."
    )
    parser.add_argument(
        "--restart", action="store_true", help="Restart Steam if changes were applied and no games are running."
    )
    parser.add_argument(
        "--notify", action="store_true", help="Send a desktop notification when changes are detected."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress status output unless an error occurs."
    )
    parser.add_argument(
        "--steam-dir", default=DEFAULT_STEAM_COMPAT_DIR, help="Path to Steam compatibilitytools.d"
    )
    parser.add_argument(
        "--heroic-dir", default=DEFAULT_HEROIC_PROTON_DIR, help="Path to Heroic proton tools"
    )

    args = parser.parse_args(argv)

    dry_run = not args.apply and args.check
    if not args.check and not args.apply:
        dry_run = False

    heroic_actions = sync_heroic_to_steam(args.heroic_dir, args.steam_dir, dry_run=dry_run)
    manifest_actions = reconcile_manifests(args.steam_dir, dry_run=dry_run)

    all_actions = heroic_actions + manifest_actions

    if not args.quiet:
        if all_actions:
            print("Steam Proton Compatibility Actions:")
            for act in all_actions:
                print(f"  {act}")
        else:
            print("All Steam Proton tools and manifests are healthy and synchronized.")

    if all_actions and not dry_run:
        if args.notify:
            notify(
                "Proton Tools Synchronized",
                "Compatibility manifests were updated. Restart Steam to apply.",
            )

        if args.restart:
            if is_game_running():
                if not args.quiet:
                    print("Notice: A game is currently running. Skipping Steam restart.")
                if args.notify:
                    notify("Steam Restart Deferred", "A game is active. Restart Steam after exiting your game.")
            else:
                if not args.quiet:
                    print("Restarting Steam service...")
                if restart_steam():
                    if not args.quiet:
                        print("Steam restarted successfully.")
                else:
                    if not args.quiet:
                        print("Failed to restart Steam automatically.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
