# Testing Guide

This project uses `pytest` with `pytest-asyncio` and `discord.ext.test` (`dpytest`).

## Test Structure

- `tests/unit/`
  - Fast, isolated tests for pure functions and logic.
  - Should avoid Discord/network setup where possible.
- `tests/integration/`
  - Tests that exercise bot commands and cog behavior.
  - Use `dpytest` to send command messages and inspect responses.
- `tests/conftest.py`
  - Shared fixtures for tests.
  - The `bot` fixture configures the bot test environment and loads cogs.

## Run Tests

Run the full test suite:

```powershell
uv run python -m pytest
```

Run only unit / integration tests:

```powershell
python -m pytest tests/unit
```
```powershell
python -m pytest tests/integration
```

Run a single test file:

```powershell
python -m pytest tests/integration/test_utilities.py
```

Run one test function:

```powershell
python -m pytest tests/integration/test_utilities.py::test_about_embed_title
```

## Writing New Tests

- Keep unit tests small and deterministic.
- Prefer one behavior/assertion focus per test.
- For integration tests, ensure the required fixtures are included (for example `bot`).
- Use clear test names that describe expected behavior.
