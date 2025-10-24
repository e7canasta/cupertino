# Repository Guidelines

## Project Structure & Module Organization
The project centers on computer-vision workflows powered by `supervision` and `ultralytics`. Use `main.py` for line-crossing tracking over samples in `data/videos`, and `run_crop_image.py` for image preprocessing experiments. Keep large raw assets inside `data/` and place reusable helpers in new modules under `src/` if the logic grows beyond quick scripts. Store generated artifacts in `samples/` to keep the repo root tidy.

## Build, Test, and Development Commands
- `uv sync` installs all dependencies from `pyproject.toml` into the managed `.venv`.
- `uv run python main.py` executes the ByteTrack pipeline against `data/videos/vehicles-1280x720.mp4`.
- `uv run python run_crop_image.py` runs the image cropping and scaling demo with assets from `data/images`.
- `uv run python -m pip install -e .` (optional) enables local package-style imports when you add modules under `src/`.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and descriptive snake_case identifiers. Treat temporary notebooks or experiments as throwaway; migrate production-ready code into modules with clear docstrings. Favor type hints when integrating with Ultralytics models, and keep magic numbers near the top of each script as uppercase constants.

## Testing Guidelines
Adopt `pytest` for new automated tests and place them under `tests/`, mirroring the source layout. Name test files `test_<feature>.py` and individual tests `test_<behavior>`. Until an automated suite exists, verify changes by running both example scripts and include representative sample assets when needed. Target ≥80% coverage for new modules and document any manual QA in the pull request description.

## Commit & Pull Request Guidelines
There is no commit history yet; start with imperative, 72-character subject lines (e.g., "Add byte-track counter"). Reference GitHub issues in the body when applicable. Pull requests should describe the scenario exercised, include repro or test commands, and attach screenshots or metrics when visual output changes. Ensure large media files stay out of version control by pointing reviewers to reproducible steps.

## Data & Environment Notes
Validate that required videos or images exist before running scripts; provide download or generation instructions when introducing new assets. Keep `.env` or credentialed configuration out of source control and document required environment variables in the pull request if any.
