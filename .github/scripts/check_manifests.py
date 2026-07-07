#!/usr/bin/env python3
"""Deterministic validation of the plugin and marketplace manifests.

A stdlib-only safety net that always gates CI even if the `claude plugin
validate` CLI step is unavailable in the runner. Checks that both JSON files
parse and carry the fields Claude Code requires, and that the marketplace
entry agrees with the plugin manifest.

Usage: python3 .github/scripts/check_manifests.py
Exit 0 if valid, 1 otherwise.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"{path} does not exist"
    except json.JSONDecodeError as exc:
        return None, f"{path} is not valid JSON: {exc}"


def check():
    errors = []

    plugin, err = load(PLUGIN)
    if err:
        errors.append(err)
    else:
        for key in ("name", "version", "description"):
            if not plugin.get(key):
                errors.append(f"plugin.json missing required field '{key}'")

    market, err = load(MARKETPLACE)
    if err:
        errors.append(err)
    else:
        if not market.get("name"):
            errors.append("marketplace.json missing 'name'")
        plugins = market.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            errors.append("marketplace.json 'plugins' must be a non-empty array")
        else:
            for i, entry in enumerate(plugins):
                for key in ("name", "source"):
                    if not entry.get(key):
                        errors.append(f"marketplace.json plugins[{i}] missing '{key}'")

    # Cross-manifest agreement: the marketplace must list the plugin by name.
    if plugin and market and isinstance(market.get("plugins"), list):
        listed = {p.get("name") for p in market["plugins"]}
        if plugin.get("name") and plugin["name"] not in listed:
            errors.append(
                f"plugin.json name '{plugin['name']}' is not listed in marketplace.json plugins {sorted(listed)}"
            )

    return errors


def main():
    print("== plugin / marketplace manifest checks ==")
    errors = check()
    if errors:
        for e in errors:
            print(f"FAIL - {e}")
        print("\nManifest checks failed.")
        return 1
    print(f"PASS - {PLUGIN.name} and {MARKETPLACE.name} valid and in agreement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
