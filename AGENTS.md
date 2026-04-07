# Repository Guidelines

## Project Structure & Module Organization
This repository is a flat Python project with application modules at the repo root. Core files are `knowledge_base.py` for PostgreSQL + FAISS storage, `financial_text_splitter.py` for document parsing and chunking, `api.py` for the FastAPI service, `frontend.py` for the Streamlit UI, and `example_usage.py` for ingestion and query flows. Tests also live at the root as [`test_financial_splitter.py`](/D:/develop/Source%20Code/FinRegQA/test_financial_splitter.py) and [`test_knowledge_base.py`](/D:/develop/Source%20Code/FinRegQA/test_knowledge_base.py). Infrastructure files include `requirements.txt`, `docker-compose.yml`, and `run.py`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt`: install runtime and test dependencies.
- `docker-compose up -d`: start the local PostgreSQL instance on `localhost:5432`.
- `python run.py`: launch the FastAPI backend and Streamlit frontend together.
- `python api.py`: run only the API service for backend work.
- `python -m streamlit run frontend.py`: run only the UI.
- `pytest -q`: run the full test suite.
- `pytest test_knowledge_base.py -q`: run a focused test module during iteration.

## Coding Style & Naming Conventions
Follow existing Python conventions: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and descriptive module names. Keep new modules small and single-purpose, consistent with the current root-level layout. Prefer type hints for public functions and Pydantic models. There is no repo-local formatter config yet, so keep imports grouped logically and match the surrounding style before introducing tooling changes.

## Testing Guidelines
Use `pytest` for all new tests. Name files `test_*.py` and name test functions `test_*`. Add unit tests next to the existing root-level test files rather than creating a separate test package unless the project is reorganized. For database or FAISS behavior, prefer lightweight fakes and deterministic fixtures, following the pattern in `test_knowledge_base.py`.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit style with short Chinese summaries, for example `feat: 接入 LLM 进行回答` and `fix: 解决 FAISS IVF 索引的空桶问题`. Keep commits scoped and typed (`feat`, `fix`, `test`, etc.). PRs should describe the user-visible change, list any required env vars or data setup, and include API examples or UI screenshots when modifying `api.py` or `frontend.py`.

## Security & Configuration Tips
Load secrets from `.env`; do not hardcode credentials or model keys. The app reads `FINREGQA_*` variables for database, embedding model, and FAISS path settings. Treat uploaded regulation documents and generated FAISS index files as local development data unless explicitly approved for sharing.
