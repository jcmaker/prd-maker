# Contributing to prd-maker

Thanks for helping make prd-maker better! Issues, ideas, and pull requests are all welcome.

## Ways to contribute

- **Report a bug or an awkward interview question** — open an issue. Concrete examples ("I said X, it asked Y, I expected Z") are gold.
- **Suggest an improvement** — open a feature-request issue first so we can agree on scope before you build.
- **Send a PR** — for the docs, the interview guide, the PRD template, or the linter.

## Development setup

This is a prompt-asset plugin: markdown instructions plus a small standard-library Python linter. There's no build step.

Run the same checks CI runs, from the repo root:

```bash
./scripts/check-all.sh
```

All checks must pass. CI runs them on every pull request. `ruff` is optional locally (the script skips it if not installed) but CI always enforces it.

## Conventions that keep the skill healthy

- **`SKILL.md` stays thin** (≤ 150 lines) — it orchestrates; details live in `references/`.
- **Judgment in markdown, determinism in code** — interview and PRD logic are instructions; structural checks live in `validate_prd.py`.
- **The skill is language-agnostic** — it interviews and writes the PRD in the *user's* language. Keep the instruction files in English; don't hardcode a single output language.
- **One copy of each skill, two plugin manifests** — skills live once under `skills/`; `.claude-plugin/` and `.codex-plugin/` are thin packaging on top. Never fork a skill or a script per tool.

## Versioning

Semantic versioning, currently in `0.x`, so the **minor** position carries features and the **patch** position carries everything else.

| Bump | When | Example |
|---|---|---|
| **minor** (`0.2.0` → `0.3.0`) | A user can do something they could not do before: a new skill, a new command, a new output, a changed interview or PRD structure. | `/prd-to-html` — a whole new artifact the plugin can produce. |
| **patch** (`0.2.0` → `0.2.1`) | Everything else: bug fixes, docs, CI, refactors, and **widening the reach of a feature that already shipped**. | Giving `prd-to-html` an entry point in Codex and Cursor — the same conversion, reachable from more tools. |

That last row is the one people get wrong, so it is worth stating plainly: adding a file under `skills/` is not automatically a minor bump. Ask what the user can newly *do*. If the answer is "the same thing, from somewhere else," it is a patch.

Breaking changes get their own note in the release, whatever the number says — pre-1.0 the version cannot express them.

When you bump, change all four places (CI checks the two manifests agree, but nothing checks the badges):

- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- the version badge in `README.md`
- the version badge in `README.ko.md`

Releases are cut from `main` as a `vX.Y.Z` tag plus a GitHub release. Note anything a user has to know in the release body, including known limitations — shipping a rough edge is fine, hiding it is not.

## Pull requests

1. Fork the repo and branch from `main`.
2. Make your change and run `./scripts/check-all.sh`.
3. Open a PR describing **what** changed and **why**. Link the issue if there is one (`Closes #123`).
4. CI must be green. A maintainer reviews and merges — you don't need a separate approver.

Commit messages in English or Korean are both fine.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
