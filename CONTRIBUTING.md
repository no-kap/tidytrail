# Contributing to tidytrail

Thanks for your interest! tidytrail is a small, beginner-friendly project, and
contributions of every size are welcome: bug reports, tests, docs, and code.

## Getting set up

```bash
git clone https://github.com/no-kap/tidytrail.git
cd tidytrail
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run the checks before you open a pull request:

```bash
ruff check .
pytest
```

## Making a change

1. Look for an issue labeled **good first issue**, or open one to discuss your idea first.
2. Create a branch: `git checkout -b my-change`.
3. Write a test that fails without your change, then make it pass.
4. Keep the pull request small and focused, and describe *why* the change is useful.
5. Update `README.md` / `CHANGELOG.md` if behavior changes.

## Ground rules

- **Use synthetic data only.** Never include real student, customer, or employee data
  in examples, tests, or issues.
- tidytrail must **never modify the input file** and must **record every change** it
  makes in the change log. New cleaning rules need a change `kind` and tests.
- Prefer the standard library. New dependencies need a clear reason.
- AI-assisted contributions are welcome, but you are responsible for understanding,
  testing, and being able to explain every line you submit.

## Questions

Open an issue. Be kind; everyone here is learning. See the
[Code of Conduct](CODE_OF_CONDUCT.md).
