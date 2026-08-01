# Contributing

Thank you for your interest in the New Orleans surveillance mapping project.

## Getting started

1. Fork the repository and clone your fork
2. Follow the [development setup](README.md#development-setup) instructions
3. Create a branch for your work
4. Make your changes and run the tests
5. Open a pull request against `main`

## Running tests

```bash
cd nola_cameras
DJANGO_SETTINGS_MODULE=config.settings.test uv run python manage.py test --verbosity=2
```

## Linting

```bash
uv run ruff check .
uv run ruff format --check .
```

## Pull requests

- One feature or fix per PR
- Include tests for new functionality
- Make sure tests and linting pass before opening

## Reporting bugs

Open an issue with steps to reproduce and what you expected to happen.
