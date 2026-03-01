# Contributing to CertGuard

Thank you for your interest in contributing to CertGuard! This guide will help you
get started with development, testing, and submitting pull requests.

## Setup

CertGuard requires Python 3.11+ and PostgreSQL 16+.

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-org/certguard.git
   cd certguard
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Set up PostgreSQL:**

   Create a database for development:

   ```bash
   createdb certguard
   ```

   Set the database URL environment variable:

   ```bash
   export CERTGUARD_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/certguard"
   ```

4. **Run database migrations:**

   ```bash
   alembic upgrade head
   ```

## Test

The test suite uses pytest with pytest-asyncio. Tests run against an SQLite backend
by default so PostgreSQL is not required for most test runs.

**Run all tests:**

```bash
pytest -v
```

**Run tests with coverage:**

```bash
pytest --cov=src/certguard -v
```

**Run linting and type checks:**

```bash
ruff check src/
mypy src/certguard/ --ignore-missing-imports
```

**Run security analysis:**

```bash
bandit -r src/certguard/ -q
```

All of these checks run automatically in CI on every pull request. Please make sure
they pass locally before pushing.

## Pull Request

1. **Create a feature branch** from `main`:

   ```bash
   git checkout -b feature/your-feature main
   ```

2. **Make your changes.** Follow the existing code style — the project uses Ruff for
   linting with a line length of 100 characters. Key conventions:
   - FastAPI with async/await patterns
   - Pydantic models for all request/response schemas
   - SQLAlchemy async sessions for database operations
   - Proper HTTP status codes and error responses
   - JWT-based authentication on protected endpoints

3. **Add or update tests** for any new or changed functionality. Aim to maintain or
   improve test coverage.

4. **Run the full check suite** before submitting:

   ```bash
   pytest --cov=src/certguard -v
   ruff check src/
   mypy src/certguard/ --ignore-missing-imports
   bandit -r src/certguard/ -q
   ```

5. **Push your branch** and open a pull request against `main`. In your PR description:
   - Summarize what the change does and why
   - Reference any related issues
   - Note any breaking changes or migration steps

6. **CI must pass** before a PR can be merged. A maintainer will review your changes
   and may request modifications.

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub. Include
as much detail as possible: steps to reproduce, expected vs actual behavior, and your
environment (OS, Python version, etc.).

## License

By contributing to CertGuard, you agree that your contributions will be licensed under
the [MIT License](LICENSE).
