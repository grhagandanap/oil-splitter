# TODO: Oil Splitting Tools Development Plan

This document breaks down the development of the Oil Splitting Tools web application into actionable, step-by-step tasks, from initial setup to final deployment.

---

## Phase 1: Infrastructure & Project Setup

- [x] Initialize Git repository and standard `.gitignore`.
- [x] **Docker & Database:**
  - [x] Create `docker-compose.yml` for PostgreSQL 17 (local development).
  - [x] Spin up the database container and ensure connection stability.
- [x] **Backend Setup (FastAPI):**
  - [x] Initialize Python environment (`venv` or `poetry`).
  - [x] Install dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `pandas`, `passlib`, `python-jose`, `python-multipart`.
  - [x] Set up basic FastAPI app structure (`app/main.py`, `app/api/`, `app/core/`, `app/db/`, `app/schemas/`, `app/services/`).
  - [x] Configure environment variables (`.env`).
  - [x] Set up SQLAlchemy engine, session maker, and Base model.
  - [x] Initialize Alembic (`alembic init`) and configure it to use SQLAlchemy models.
- [x] **Frontend Setup (React):**
  - [x] Initialize React app using Tanstack Start by using pnpm package manager
  - [x] Install dependencies: `@tanstack/react-router`, `@tanstack/react-query`, `@tanstack/react-table`, `ky` (HTTP client), `tailwindcss`, `lucide-react`.
  - [x] Configure Tailwind CSS.
  - [x] Set up basic folder structure (`src/components/`, `src/features/`, `src/lib/`, `src/routes/`).

---

## Phase 2: Authentication & User Management

- [x] **Backend (Auth):**
  - [x] Create `User` SQLAlchemy model (`id`, `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser`).
  - [x] Generate Alembic migration for `users` table and apply it.
  - [x] Implement password hashing and verification utility functions (`passlib[bcrypt]`).
  - [x] Implement JWT token generation and decoding logic (`python-jose`, access + refresh).
  - [x] Create FastAPI dependency `get_current_user` to secure routes.
  - [x] Implement Auth Endpoints:
    - [x] `POST /api/v1/auth/register`
    - [x] `POST /api/v1/auth/login`
    - [x] `POST /api/v1/auth/refresh` _(bonus — silent refresh support)_
    - [x] `GET /api/v1/auth/me`
- [x] **Frontend (Auth):**
  - [x] Create API client utility for auth (`ky` instance with JWT header injection, refresh-on-401, tokens in `localStorage`).
  - [x] Build Login Page component (`/login`).
  - [x] Build Registration Page component (`/register`).
  - [x] Implement Auth Context/Provider to manage global user state.
  - [x] Setup protected routes in TanStack Router (`_app` layout redirects to `/login` when unauthenticated).

---

## Phase 3: Core Business Logic (Python Porting)

- [x] **Algorithm Extraction:**
  - [x] Extract the core logic from `Markering and Splitting.ipynb`.
  - [x] Create Python service modules in `app/services/` (`marker_engine.py`, `gap_filler.py`, `splitter_engine.py`).
  - [x] Implement the "Auto Marker Machine" logic (TOP_WAY, BOTTOM_WAY, first-marker tolerance, squeeze_machine).
  - [x] Implement pattern-based gap filling for missing data ("p" filling): auto bfill/ffill for leading/trailing, interactive resolution for middle gaps.
  - [x] Implement the KH-weighted Splitting calculation for Oil, Gas, Water, Water Injection.
- [x] **Testing:**
  - [x] Create synthetic test datasets matching the required inputs.
  - [x] Write `pytest` unit tests to verify the ported logic (32 tests, all passing).

---

## Phase 4: Projects & Data Ingestion

- [x] **Backend (Projects & Datasets):**
  - [x] Create `Project` model (`id`, `owner_id`, `name`, `description`).
  - [x] Create `Dataset` model (`id`, `project_id`, `kind`, `source`, `raw_data` JSONB, `validation_errors` JSONB, `is_valid`).
  - [x] Generate and apply Alembic migrations.
  - [x] Implement CRUD endpoints for Projects (`/api/v1/projects`).
  - [x] Implement Data Parsing logic (CSV, TSV for pasting, XLSX using `openpyxl`).
  - [x] Implement Row-Level Validation logic for the 6 dataset kinds (Marker, Marker List, Completion, Production, Lumping, Wells).
    - Type coercion + missing-value detection per required column.
    - Cross-column rule: `Perf Bottom > Perf Top` for completion rows.
    - Status enum check: `Perf Status` must be `perforation` or `squeeze` (case-insensitive).
    - Non-negative numeric guards on `Depth`, `Perf Top/Bottom`, production fluid columns, and `Lumping`.
    - Lumping input accepts long format (`Zone`, `Well`, `Lumping`) and stores a pivoted zone × well matrix.
    - Empty-dataset detection.
  - [x] Implement Ingestion Endpoints:
    - [x] `POST /api/v1/projects/{id}/datasets/paste` (JSON data)
    - [x] `POST /api/v1/projects/{id}/datasets/upload` (Multipart file upload)
    - [x] `POST /api/v1/projects/{id}/datasets/workbook-sheets` (Excel sheet inspection)
    - [x] `GET /api/v1/projects/{id}/datasets`
  - [x] Backend tests: 33 ingestion tests + explicit marker-tolerance scenario tests (68 passing total).
- [x] **Frontend (Ingestion UI):**
  - [x] Create Projects Dashboard (list projects, create new project button) at `/dashboard`.
  - [x] Create Project Detail Layout at `/projects/$projectId` (tabs for Inputs vs Results).
  - [x] Build "Data Inputs" view with 6 specific tabs (Marker, Sand, Completion, Production, Lumping, Wells).
  - [x] For each tab, implement UI components:
    - [x] Paste Dialog (textarea to paste TSV/CSV with auto-delimiter detection).
    - [x] Upload Button (file picker for CSV/TSV/XLSX).
    - [x] Excel sheet picker for multi-sheet workbooks.
    - [x] Required-column caution block for every dataset type.
    - [x] TanStack Table to preview parsed/uploaded data (first 25 rows).
    - [x] Validation Errors panel (row + column + message, returned from backend).
  - [x] Wells tab accepts a real `Well` list dataset.
  - [x] All new components use modern Tailwind v4 syntax (`bg-(--var)` shortcut — no obsolete `[var(...)]`).

---

## Phase 5: Execution & Results Dashboard

- [ ] **Backend (Execution):**
  - [ ] Create `Run` or `SplitResult` model to store calculated outputs per project.
  - [ ] Implement Endpoint `POST /api/v1/projects/{id}/split/run`:
    - Fetch active, valid datasets for the project.
    - Pass data to `splitter_engine.py`.
    - Save results to the database.
  - [ ] Implement Endpoint `GET /api/v1/projects/{id}/split/runs/{run_id}` to fetch results.
- [ ] **Frontend (Results):**
  - [ ] Build a "Run Calculation" button/interface in the Project Detail view.
  - [ ] Handle loading states during algorithm execution.
  - [ ] Build Results Dashboard to display the allocated splitting values (using TanStack Table).
  - [ ] Implement "Export to CSV/Excel" functionality on the frontend for the results table.

---

## Phase 6: Polish & Deployment

- [ ] **Refinement:**
  - [ ] Add loading skeletons/spinners across the app.
  - [ ] Ensure mobile responsiveness for tables and forms (Tailwind).
  - [ ] End-to-End manual testing of the entire flow.
- [ ] **Deployment (Backend):**
  - [ ] Configure `uvicorn` startup script or `Procfile`.
  - [ ] Set up environment variables securely on FastAPI Cloud (or equivalent PaaS like Render/Railway).
  - [ ] Deploy FastAPI application and run remote migrations.
- [ ] **Deployment (Frontend):**
  - [ ] Ensure API base URL is configured via Vite env variables (`.env.production`).
  - [ ] Connect the GitHub repository to Cloudflare Pages.
  - [ ] Configure build settings (`npm run build`, output dir: `dist`).
  - [ ] Deploy and verify CORS settings between Cloudflare Pages and the Backend API.
