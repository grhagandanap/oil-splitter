# TODO: Oil Splitting Tools Development Plan

This document breaks down the development of the Oil Splitting Tools web application into actionable, step-by-step tasks, from initial setup to final deployment.

---

## Phase 1: Infrastructure & Project Setup

- [ ] Initialize Git repository and standard `.gitignore`.
- [ ] **Docker & Database:**
  - [ ] Create `docker-compose.dev.yml` for PostgreSQL 17 (local development).
  - [ ] Spin up the database container and ensure connection stability.
- [ ] **Backend Setup (FastAPI):**
  - [ ] Initialize Python environment (`venv` or `poetry`).
  - [ ] Install dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `pandas`, `passlib`, `python-jose`, `python-multipart`.
  - [ ] Set up basic FastAPI app structure (`app/main.py`, `app/api/`, `app/core/`, `app/db/`, `app/models/`, `app/schemas/`, `app/services/`).
  - [ ] Configure environment variables (`.env`).
  - [ ] Set up SQLAlchemy engine, session maker, and Base model.
  - [ ] Initialize Alembic (`alembic init`) and configure it to use SQLAlchemy models.
- [ ] **Frontend Setup (React):**
  - [ ] Initialize React app using Tanstack Start by using pnpm package manager
  - [ ] Install dependencies: `@tanstack/react-router`, `@tanstack/react-query`, `@tanstack/react-table`, `ky` or `fetch` wrappers, `tailwindcss`, `lucide-react`.
  - [ ] Configure Tailwind CSS.
  - [ ] Set up basic folder structure (`src/components/`, `src/features/`, `src/lib/`, `src/routes/`).

---

## Phase 2: Authentication & User Management

- [ ] **Backend (Auth):**
  - [ ] Create `User` SQLAlchemy model (`id`, `email`, `hashed_password`, `full_name`, `is_active`).
  - [ ] Generate Alembic migration for `users` table and apply it.
  - [ ] Implement password hashing and verification utility functions.
  - [ ] Implement JWT token generation and decoding logic.
  - [ ] Create FastAPI dependency `get_current_user` to secure routes.
  - [ ] Implement Auth Endpoints:
    - [ ] `POST /api/v1/auth/register`
    - [ ] `POST /api/v1/auth/login`
    - [ ] `GET /api/v1/auth/me`
- [ ] **Frontend (Auth):**
  - [ ] Create API client utility for auth (handling JWT in headers, storing tokens in localStorage/cookies).
  - [ ] Build Login Page component.
  - [ ] Build Registration Page component.
  - [ ] Implement Auth Context/Provider to manage global user state.
  - [ ] Setup protected routes in TanStack Router (redirect to login if unauthenticated).

---

## Phase 3: Core Business Logic (Python Porting)

- [ ] **Algorithm Extraction:**
  - [ ] Extract the core logic from `Markering and Splitting.ipynb`.
  - [ ] Create Python service modules in `app/services/` (e.g., `splitter_engine.py`).
  - [ ] Implement the "Auto Marker Machine" logic (handling TOP WAY, BOTTOM WAY, etc.).
  - [ ] Implement pattern-based gap filling for missing data ("p" filling).
  - [ ] Implement the KH-weighted Splitting calculation for Oil, Gas, Water, Water Injection.
- [ ] **Testing:**
  - [ ] Create synthetic test datasets matching the required 5 inputs.
  - [ ] Write `pytest` unit tests to verify the ported logic perfectly matches the Jupyter Notebook's outputs.

---

## Phase 4: Projects & Data Ingestion

- [ ] **Backend (Projects & Datasets):**
  - [ ] Create `Project` model (`id`, `owner_id`, `name`, `description`).
  - [ ] Create `Dataset` model (`id`, `project_id`, `kind`, `source`, `raw_data` JSONB, `validation_errors` JSONB, `is_valid`).
  - [ ] Generate and apply Alembic migrations.
  - [ ] Implement CRUD endpoints for Projects (`/api/v1/projects`).
  - [ ] Implement Data Parsing logic (CSV, TSV for pasting, XLSX using `openpyxl`).
  - [ ] Implement Row-Level Validation logic for the 5 dataset kinds (Marker, Sand, Completion, Production, Lumping).
  - [ ] Implement Ingestion Endpoints:
    - [ ] `POST /api/v1/projects/{id}/datasets/paste` (JSON data)
    - [ ] `POST /api/v1/projects/{id}/datasets/upload` (Multipart file upload)
    - [ ] `GET /api/v1/projects/{id}/datasets`
- [ ] **Frontend (Ingestion UI):**
  - [ ] Create Projects Dashboard (list projects, create new project button).
  - [ ] Create Project Detail Layout (tabs for Inputs vs Results).
  - [ ] Build "Data Inputs" view with 6 specific tabs (Marker, Sand, Completion, Production, Lumping, Well).
  - [ ] For each tab, implement UI components:
    - [ ] Paste Dialog (textarea to paste TSV/CSV).
    - [ ] Upload Button (file picker).
    - [ ] TanStack Table to preview parsed/uploaded data.
    - [ ] Validation Errors panel (displaying row-specific errors returned from backend).

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
