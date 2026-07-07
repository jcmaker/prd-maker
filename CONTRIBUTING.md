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

All three must pass. CI runs them on every pull request.

## Conventions that keep the skill healthy

- **`SKILL.md` stays thin** (≤ 150 lines) — it orchestrates; details live in `references/`.
- **Judgment in markdown, determinism in code** — interview and PRD logic are instructions; structural checks live in `validate_prd.py`.
- **The skill is language-agnostic** — it interviews and writes the PRD in the *user's* language. Keep the instruction files in English; don't hardcode a single output language.
- **Two plugin manifests, one skill** — if you bump the version, bump it in **both** `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (CI checks they agree).

## Pull requests

1. Fork the repo and branch from `main`.
2. Make your change and run the three checks above.
3. Open a PR describing **what** changed and **why**. Link the issue if there is one (`Closes #123`).
4. CI must be green. A maintainer reviews and merges — you don't need a separate approver.

Commit messages in English or Korean are both fine.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
