# Contributing to OmniMem

Thanks for considering a contribution. OmniMem is small and opinionated, so a quick read of this file before opening a PR will save us both time.

## Where to start

- **Bug**: open an issue with the [bug template](.github/ISSUE_TEMPLATE/bug_report.md). Include `omnimem doctor --json`, the failing command, and the full traceback.
- **Feature**: open a [feature request](.github/ISSUE_TEMPLATE/feature_request.md) **first**. Don't write code before there's agreement on the design — OmniMem deliberately keeps scope tight (see `ROADMAP.md`).
- **Question**: use the [question template](.github/ISSUE_TEMPLATE/question.md) or check `docs/faq.md`.

## Local dev

```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
./scripts/setup.sh         # creates venv, installs deps, bootstraps the model
source venv/bin/activate
python -m unittest discover -s tests -v
```

## Coding standards

- **Stdlib-first.** Tests must run on a bare Python 3.10 with only PyYAML installed. Heavy deps (chromadb, sentence-transformers, kreuzberg) are imported lazily inside functions, not at module top level.
- **One feature per module.** New CLI verbs go in `omni_<feature>.py`; the unified `omnimem.py` dispatcher only wires them.
- **Tests are mandatory.** Every PR adds tests for the new behavior. Tests use `unittest` (no pytest) so they run with no extra install.
- **Docs are mandatory.** Every user-visible change updates the relevant `docs/*.md` and the `CHANGELOG.md`.

## PR checklist

Before opening:

- [ ] `python -m unittest discover -s tests` passes locally
- [ ] `python -m benchmarks.run_all` still produces sensible numbers (no >10% regression on latency / accuracy benchmarks)
- [ ] CLI smoke test for any new flag (`python -c "from omnimem import build_parser; ..."`)
- [ ] `CHANGELOG.md` entry under the next release header
- [ ] Updated `docs/<feature>.md` if user-facing
- [ ] No `Co-Authored-By: Claude` (or any LLM identity) trailer in commits

## Adding a new codemap language

1. Write a parser in `omni_codemap.py` that returns the standard model dict (`{language, path, module_doc, imports, classes, functions}`).
2. Register it in `LANGUAGE_PARSERS`.
3. Add the file extensions to `_LANGUAGE_BY_EXTENSION`, `_EXTENSIONS_BY_LANGUAGE`, and `SUPPORTED_LANGUAGES`.
4. Add a synthetic ground-truth fixture and target case in `benchmarks/bench_codemap_accuracy.py` (`CASES`).
5. Add tests in `tests/test_codemap_multilang.py`.
6. Update `docs/codemap.md` with the new language row.

## Adding a new redaction pattern

1. Add the regex to `omni_redact._PATTERNS` with a snake_case name.
2. Add a positive case and a negative case (clean text that should NOT match) to `tests/test_redact.py`.
3. Add the pattern to the table in `docs/redact.md`.

## Reporting a security issue

If you find a way to leak secrets, escalate privileges, or persist arbitrary code in the vault that's executed by an agent, please **do not open a public issue**. Email the maintainer or use GitHub's private vulnerability reporting.

## License

MIT — by contributing you agree your work is licensed under the same terms.
