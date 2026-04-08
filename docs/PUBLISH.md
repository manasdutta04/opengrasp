# Publishing `openapply` to PyPI

The package is configured in `pyproject.toml` with the console entry point `openapply`.

## One-time: PyPI credentials

1. Create an API token on [pypi.org](https://pypi.org/manage/account/token/) (scope: entire account or project `openapply` after the first upload).
2. Set environment variables (do **not** commit tokens):

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-YOUR_TOKEN_HERE"
```

Or add the same keys to a local `.env` file (ignored by git); `scripts/publish.ps1` reads `TWINE_USERNAME` and `TWINE_PASSWORD` from `.env`.

## Build and validate

```powershell
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

## Upload

**TestPyPI (recommended first):**

```powershell
python -m twine upload --repository testpypi dist/*
```

**Production PyPI:**

```powershell
python -m twine upload dist/*
```

Or use the helper from the repo root:

```powershell
.\scripts\publish.ps1 -TestPyPI   # dry-run build + check if you omit -TestPyPI/-PyPI
.\scripts\publish.ps1 -PyPI
```

## After release

Users install with:

```bash
pip install openapply
openapply setup
```

## Version bumps

Increase `version` in `pyproject.toml` before each new upload; PyPI rejects re-uploading the same version.
