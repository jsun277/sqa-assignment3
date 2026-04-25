# KIS — Kinetic Intelligence System

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run tests

```bash
pytest
```

## Regenerate coverage report

```bash
coverage run --branch --source=src -m pytest && coverage report -m && coverage html
```

The HTML report is written to `htmlcov/index.html`.
