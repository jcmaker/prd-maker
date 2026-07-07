# Security Policy

prd-maker is a prompt-asset plugin plus a small standard-library Python linter, so its runtime surface is small — but we take reports seriously.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Email **jcmaker0627@gmail.com** with:

- a description of the issue and its impact,
- steps to reproduce,
- any suggested fix.

You'll get an acknowledgement, and we'll agree on a fix and disclosure timeline with you.

## Scope

Most relevant: anything where following the skill's instructions or running `validate_prd.py` could execute unintended code or leak data. The general prompt-injection behavior of the underlying agent (Claude Code, Codex, etc.) is out of scope here — report that to the agent's vendor.
