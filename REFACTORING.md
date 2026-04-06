# Refactoring Plan

## Phase 1: Critical Fixes (Stability & Reliability)
- [ ] **Fix File Encoding Issues**
    - [ ] Explicitly set `encoding='utf-8'` in all `open()` calls (e.g., `run_cli.py`, `src/config.py`).
    - [ ] Ensure `sys.stdin` and `sys.stdout` handling supports UTF-8 on Windows.
- [x] **Harden Network Requests (`src/updater.py`)**
    - [x] Add `timeout` to `requests.get()`.
    - [x] Handle `requests.exceptions.RequestException`.
    - [x] Check `response.status_code` before parsing JSON.
    - [x] Use `response.json()` instead of `json.loads(response.text)`.
- [x] **Improve Error Handling**
    - [x] Remove broad `try...except Exception` blocks where possible (e.g., `src/convert.py`).
    - [x] Log specific errors instead of silently failing or printing to stdout.

## Phase 2: Modernization (Code Quality)
- [ ] **Remove Python 2 Compatibility**
    - [ ] Remove `six` dependency.
    - [ ] Remove `from __future__` imports.
    - [ ] Remove `(object)` inheritance from classes.
    - [ ] Replace `u''` string prefixes if present.
- [ ] **Add Type Hints**
    - [ ] Add type annotations to core functions in `src/convert.py`.
    - [ ] Add type annotations to `src/pdf/pdf.py` and `src/pdf/bookmark.py`.
- [ ] **Code Formatting & Linting**
    - [ ] Apply `black` or `ruff` formatting.
    - [ ] Sort imports using `isort`.

## Phase 3: Architecture Refactoring
- [ ] **Refactor `convert_dir_text`**
    - [ ] Create a `ConversionConfig` dataclass to replace the 11+ arguments.
    - [ ] Break down the monolithic function into smaller, testable units.
- [ ] **Improve Configuration Management**
    - [ ] Move config file handling to a dedicated `ConfigManager` class.
    - [ ] Use `appdirs` or `pathlib` to store config in the correct user data directory.
- [ ] **Decouple `Pdf` Class**
    - [ ] Remove file system side-effects (auto-generating `_new` filenames) from the class.
    - [ ] Allow passing file-like objects instead of just paths.

## Phase 4: Performance & Optimization
- [ ] **Optimize Regex**
    - [ ] Pre-compile regex patterns in `src/convert.py`.
    - [ ] Optimize `split_page_num` loop.
- [ ] **Optimize PDF Operations**
    - [ ] Review `copy_reader_to_writer` necessity with modern `pypdf`.

## Phase 5: Testing
- [ ] **Expand Test Coverage**
    - [ ] Add unit tests for `Pdf` class.
    - [ ] Add integration tests for the CLI entry point.
