# Contributing to videoMerge

Thanks for helping improve videoMerge. This guide covers local setup,
validation, and the pull request process.

## Ways to contribute

- **Report a bug** using the repository's bug report form.
- **Request a feature** using the feature request form.
- **Send a pull request** after opening an issue for non-trivial changes.
- **Report a vulnerability privately** by following [SECURITY.md](SECURITY.md).

## Prerequisites

- Python 3.10 or newer (CI validates with 3.12; standard library only — no pip
  dependencies)
- ffmpeg on `PATH` (needed to run the tool, not to validate the source)
- gitleaks 8.30.1 or newer

## Set up from a clean clone

```bash
git clone https://github.com/iamteedoh/videoMerge.git
cd videoMerge
```

No virtual environment or dependency install is required; the script uses only
the Python standard library. Never commit `.env` files, tokens, credentials, or
personal media paths.

## Run the validation suite

Run the same checks that protect `main`:

```bash
python -m compileall -q .
python -c "import merge_videos"
gitleaks git . --config .gitleaks.toml --redact --no-banner
```

When changing merge or encoder behavior, exercise the script manually against a
scratch directory of short sample clips before opening a PR.

## Project layout

- `merge_videos.py` — the whole tool: encoder detection and selection,
  folder/clip discovery, optional sanitizing re-encode, ffmpeg concat merge,
  and the interactive prompts
- `.github/workflows/` — source validation and source-only release automation

## Pull request process

1. Create a branch from `main`.
2. Make the smallest complete change and update documentation.
3. Run the full validation suite above.
4. Use a [Conventional Commit](https://www.conventionalcommits.org/) PR title:
   `feat:`, `fix:`, `docs:`, `refactor:`, `ci:`, `test:`, or `chore:`.
5. Complete the pull request template and link the related public issue.
6. Wait for all required checks to pass, then squash-merge.

The PR title becomes the squash commit subject and drives release-please:
`fix:` creates a patch release, `feat:` creates a minor release, and a `!` or
`BREAKING CHANGE:` footer creates a breaking release.

## License

By contributing, you agree that your contributions are licensed under the
project's [GNU General Public License v3](LICENSE).
