#!/bin/sh
export PYTHONIOENCODING=utf-8
set -e
cd "$(dirname "$0")/.."

python3 skills/prd-maker/scripts/test_validate_prd.py
python3 .github/scripts/check_skill_structure.py
python3 .github/scripts/check_manifests.py
