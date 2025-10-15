# Repository Guidelines

## Project Structure & Module Organization
The `server/` directory hosts the FastAPI backend, with `app.py` as the main entrypoint and supporting modules (e.g., `streaming_controller.py`, `lm_studio_client.py`, `rules_manager.py`) handling the three-layer response flow. Configuration defaults live in `server/config/`, while transient uploads resolve to `server/uploads/` at runtime. The `chatty-local-glow/` folder contains the Vite + React TypeScript UI; assets sit in `public/` and feature code resides in `src/`. Docs live in `docs/`. Integration tests, fixtures, and utility scripts live in `testing stuff/`.

## Build, Test, and Development Commands
Run `Setup.bat` once to create `.venv` and install Python dependencies; afterwards activate with `.venv\Scripts\Activate.ps1`. Launch the backend via `Run.bat` or manually with `cd server && uvicorn app:app --host 127.0.0.1 --port 8010`. Ensure LM Studio serves a model on `http://127.0.0.1:1234` before testing AI features. For the UI, run `cd chatty-local-glow && npm install` (or `bun install`), then `npm run dev` or `npm run build`/`npm run preview` before packaging.

## Coding Style & Naming Conventions
Follow PEP 8: four-space indentation, snake_case modules (`file_handler.py`) and functions, PascalCase classes, and include type hints for new interfaces. Centralize logging with the shared `logging.getLogger(__name__)` pattern used in `server/app.py`. Document complex flows with docstrings or inline comments near orchestration points. In the frontend, keep components in PascalCase `.tsx` files, colocate hooks under `src/lib` or `src/hooks`, and rely on Tailwind utility classes plus the existing design tokens. Run `npm run lint` before committing UI changes.

## Testing Guidelines
Python regression tests live in `testing stuff/`; execute `python ".\testing stuff\test_comprehensive_suite.py"` from the repo root for the end-to-end sweep. Target specific concerns with scripts like `test_plotly_integration.py`, `test_rules_system.py`, or `test_running_server.py`. Provide fixture updates under the same folder and avoid committing generated output in `server/uploads/`. Frontend tests are manual; smoke-test the streaming UI after backend changes.

## Commit & Pull Request Guidelines
Keep commit subjects short, imperative, and descriptive (e.g., `Add streaming telemetry guard`). Group related edits together and note user-facing impact in the body. PRs should outline the problem, the approach, and verification steps; attach screenshots or recordings for UI tweaks, link related issues, and call out configuration changes to `server/config/rules.json` or dependency bumps.

## Security & Configuration Tips
Never check sensitive datasets into `uploads/`; use `.gitignore`d local files instead. Validate LM Studio servers before demos, and update rule or prompt files via PR so reviewers can confirm assistant constraints. When touching execution logic, double-check sandbox restrictions stay intact (`code_executor.py`, `validation_engine.py`).





