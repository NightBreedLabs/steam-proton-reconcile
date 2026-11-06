#!/usr/bin/env python3
"""
Unit tests for steam_proton_reconcile
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import steam_proton_reconcile as reconciler


class TestSteamProtonReconcile(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_steam_proton_")
        self.steam_dir = os.path.join(self.test_dir, "compatibilitytools.d")
        self.heroic_dir = os.path.join(self.test_dir, "heroic_tools")
        os.makedirs(self.steam_dir)
        os.makedirs(self.heroic_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _create_tool(self, base_dir, folder_name, key, display_name, meta=None):
        tool_dir = os.path.join(base_dir, folder_name)
        os.makedirs(tool_dir, exist_ok=True)
        vdf_path = os.path.join(tool_dir, "compatibilitytool.vdf")
        vdf_content = f'''"compatibilitytools"
{{
  "compat_tools"
  {{
    "{key}"
    {{
      "install_path" "."
      "display_name" "{display_name}"
      "from_oslist"  "windows"
      "to_oslist"    "linux"
    }}
  }}
}}
'''
        with open(vdf_path, "w", encoding="utf-8") as f:
            f.write(vdf_content)

        if meta:
            meta_path = os.path.join(tool_dir, ".protonplus")
            import json
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f)

        return tool_dir

    def test_parse_manifest(self):
        tool_dir = self._create_tool(
            self.steam_dir, "GE-Proton10-34", "GE-Proton10-34", "GE-Proton10-34"
        )
        vdf_path = os.path.join(tool_dir, "compatibilitytool.vdf")
        manifest = reconciler.parse_manifest(vdf_path)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["key"], "GE-Proton10-34")
        self.assertEqual(manifest["display_name"], "GE-Proton10-34")

    def test_write_manifest(self):
        tool_dir = self._create_tool(
            self.steam_dir, "ToolA", "OriginalKey", "OriginalDisplay"
        )
        vdf_path = os.path.join(tool_dir, "compatibilitytool.vdf")
        success = reconciler.write_manifest(vdf_path, "NewKey", "NewDisplay")
        self.assertTrue(success)

        updated = reconciler.parse_manifest(vdf_path)
        self.assertEqual(updated["key"], "NewKey")
        self.assertEqual(updated["display_name"], "NewDisplay")

    def test_reconcile_collision_detection_and_fix(self):
        self._create_tool(
            self.steam_dir,
            "Proton-CachyOS Latest",
            "Proton-CachyOS Latest",
            "Proton-CachyOS Latest",
            meta={"variant_id": "x86-64"},
        )
        self._create_tool(
            self.steam_dir,
            "Proton-CachyOS Latest-x86_64_v3",
            "Proton-CachyOS Latest",
            "Proton-CachyOS Latest",
            meta={"variant_id": "x86-64-v3"},
        )

        actions = reconciler.reconcile_manifests(self.steam_dir, dry_run=False)
        self.assertTrue(any("Collision detected" in a for a in actions))

        m_base = reconciler.parse_manifest(
            os.path.join(self.steam_dir, "Proton-CachyOS Latest", "compatibilitytool.vdf")
        )
        m_v3 = reconciler.parse_manifest(
            os.path.join(self.steam_dir, "Proton-CachyOS Latest-x86_64_v3", "compatibilitytool.vdf")
        )

        self.assertNotEqual(m_base["key"], m_v3["key"])
        self.assertNotEqual(m_base["display_name"], m_v3["display_name"])

    def test_sync_heroic_to_steam(self):
        self._create_tool(
            self.heroic_dir,
            "Proton-Wineland Latest-x86_64_v3",
            "Proton-Wineland Latest-x86_64_v3",
            "Proton-Wineland Latest (x86_64_v3)",
        )

        actions = reconciler.sync_heroic_to_steam(
            self.heroic_dir, self.steam_dir, dry_run=False
        )
        self.assertEqual(len(actions), 1)
        self.assertIn("Link Heroic tool", actions[0])

        steam_linked = os.path.join(self.steam_dir, "Proton-Wineland Latest-x86_64_v3")
        self.assertTrue(os.path.islink(steam_linked))
        self.assertTrue(os.path.isfile(os.path.join(steam_linked, "compatibilitytool.vdf")))

    def test_sync_heroic_skips_existing_keys(self):
        # Already present in steam
        self._create_tool(
            self.steam_dir,
            "GE-Proton10-34",
            "GE-Proton10-34",
            "GE-Proton10-34",
        )
        # Present in heroic under another folder name but same key
        self._create_tool(
            self.heroic_dir,
            "Proton-GE-Proton10-34",
            "GE-Proton10-34",
            "GE-Proton10-34",
        )

        actions = reconciler.sync_heroic_to_steam(
            self.heroic_dir, self.steam_dir, dry_run=False
        )
        self.assertEqual(len(actions), 0)


if __name__ == "__main__":
    unittest.main()
