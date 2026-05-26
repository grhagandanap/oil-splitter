# Oil Splitter - TODO List

## Phase 1: Environment Setup
- [x] Initialize Git repository
- [x] Setup monorepo structure (`/frontend` and `/backend`)
- [x] Configure backend environment (FastAPI, Neon DB connection, Alembic)
- [x] Configure frontend environment (Vite + React + TanStack Router + TailwindCSS + Shadcn UI)

## Phase 2: Backend Auth & Database
- [x] Implement DB schema and Alembic migrations (User, Project, DataFiles, ExecutionHistory)
- [x] Implement User authentication models
- [x] Create `/auth/register` and `/auth/login` API endpoints (bcrypt hashing)
- [x] Setup JWT issuance and validation middleware for protected routes

## Phase 3: Frontend Scaffolding & Auth UI
- [x] Implement application layout and TanStack routing
- [x] Build Shadcn UI forms for Login and Registration
- [x] Integrate frontend auth state with backend JWT
- [x] Build the main Dashboard UI (Projects List view)

## Phase 4: Core Logic & Upload API
- [x] Setup local storage (or AWS S3) integration for file uploads
- [x] Create API endpoints for Project creation and retrieving project history
- [x] Create API endpoints for handling the 5 required dataset uploads
- [x] Port Jupyter Notebook logic (`Markering and Splitting (GG v1).ipynb`) to Python module (`services/engine.py`)
- [x] Handle Pandas edge cases and optimize processing for the execution engine

## Phase 5: Execution UI & Results
- [ ] Build the multi-step upload wizard component in React (for Marker, Well, Production, Completion, Lumping)
- [ ] Add an "Execute" feature triggering backend background processing
- [ ] Build a live loading/polling state (via TanStack Query) to monitor processing status
- [ ] Implement final report generation and enable user downloads (Excel/CSV)

## Phase 6: Deployment
- [ ] Provision and configure Neon Serverless PostgreSQL database
- [ ] Deploy FastAPI backend on Railway (or FastAPI Cloud) and set environment variables
- [ ] Deploy React Vite frontend on Cloudflare Pages
- [ ] Perform final QA testing for full end-to-end user flow
