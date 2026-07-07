#!/usr/bin/env python3
"""Deterministic validation of the plugin and marketplace manifests.

A stdlib-only safety net that always gates CI even if the platform CLIs
(`claude plugin validate`, Codex tooling) are unavailable in the runner.
Checks both the Claude Code and Codex manifest pairs: that each JSON file
parses, carries its required fields, that each marketplace lists its plugin,
and that the two plugin manifests do not drift on name/version.

Usage: python3 .github/scripts/check_manifests.py
Exit 0 if valid, 1 otherwise.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

CLAUDE_PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKET = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKET = ROOT / ".agents" / "plugins" / "marketplace.json"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"{path.relative_to(ROOT)} does not exist"
    except json.JSONDecodeError as exc:
        return None, f"{path.relative_to(ROOT)} is not valid JSON: {exc}"


def check_pair(label, plugin_path, market_path):
    """Validate one plugin.json + marketplace.json pair. Returns (errors, plugin_dict)."""
    errors = []

    plugin, err = load(plugin_path)
    if err:
        errors.append(err)
    else:
        for key in ("name", "version", "description"):
            if not plugin.get(key):
                errors.append(f"[{label}] {plugin_path.name} missing required field '{key}'")

    market, err = load(market_path)
    if err:
        errors.append(err)
    else:
        if not market.get("name"):
            errors.append(f"[{label}] marketplace missing 'name'")
        plugins = market.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append(f"[{label}] marketplace 'plugins' must be a non-empty array")
        else:
            for i, entry in enumerate(plugins):
                for key in ("name", "source"):
                    if not entry.get(key):
                        errors.append(f"[{label}] marketplace plugins[{i}] missing '{key}'")

    # The marketplace must list the plugin by name.
    if plugin and market and isinstance(market.get("plugins"), list):
        listed = {p.get("name") for p in market["plugins"]}
        if plugin.get("name") and plugin["name"] not in listed:
            errors.append(
                f"[{label}] plugin name '{plugin['name']}' is not listed in its marketplace {sorted(listed)}"
            )

    return errors, plugin


def check():
    errors = []

    claude_errs, claude_plugin = check_pair("claude", CLAUDE_PLUGIN, CLAUDE_MARKET)
    codex_errs, codex_plugin = check_pair("codex", CODEX_PLUGIN, CODEX_MARKET)
    errors += claude_errs + codex_errs

    # Cross-platform agreement: the two plugin manifests must not drift.
    if claude_plugin and codex_plugin:
        for key in ("name", "version"):
            if claude_plugin.get(key) != codex_plugin.get(key):
                errors.append(
                    f"plugin manifests disagree on '{key}': "
                    f"claude={claude_plugin.get(key)!r} vs codex={codex_plugin.get(key)!r}"
                )

    return errors


def main():
    print("== plugin / marketplace manifest checks (Claude Code + Codex) ==")
    errors = check()
    if errors:
        for e in errors:
            print(f"FAIL - {e}")
        print("\nManifest checks failed.")
        return 1
    print("PASS - Claude Code and Codex manifests valid, in agreement, and version-aligned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
