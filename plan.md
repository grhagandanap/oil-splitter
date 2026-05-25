# Oil Splitter - Application Plan

## 1. Project Overview
"Oil Splitter" is a specialized, fullstack web application tailored for reservoir and petroleum engineers. The application automates the process of mapping geological markers, completions (perforations/squeezes), and sand data against well production history over time. 

Users can upload their datasets, execute the proprietary data processing logic, and track project history in a professional, elegant interface.

---

## 2. Technology Stack

### Frontend
- **Framework:** React.js (via Vite)
- **Routing & State:** TanStack Router & TanStack Query (as requested)
- **UI Components:** Shadcn UI + TailwindCSS (for an elegant, professional, and consistent design)
- **Hosting:** Cloudflare Pages

### Backend
- **Framework:** FastAPI (Python) - Perfect for handling data science/Pandas workloads
- **Data Processing:** `pandas` and `numpy` (translating the core logic from the Jupyter Notebook)
- **Hosting:** Railway (or FastAPI Cloud)

### Database
- **Provider:** Neon (Serverless PostgreSQL)
- **ORM:** SQLAlchemy or SQLModel
- **Migrations:** Alembic
- **Authentication:** JWT (JSON Web Tokens) with `bcrypt` for secure password hashing

---

## 3. Database Schema Design (High-Level)

1. **User**
   - `id` (UUID)
   - `email` (String, unique)
   - `hashed_password` (String, bcrypt)
   - `created_at` (Timestamp)

2. **Project**
   - `id` (UUID)
   - `user_id` (UUID, Foreign Key)
   - `name` (String)
   - `description` (Text, optional)
   - `status` (Enum: pending, processing, completed, failed)
   - `created_at` (Timestamp)

3. **DataFiles**
   - `id` (UUID)
   - `project_id` (UUID, Foreign Key)
   - `file_type` (Enum: marker, well, production, completion, lumping)
   - `s3_url` / `storage_path` (String)
   - `uploaded_at` (Timestamp)

4. **ExecutionHistory**
   - `id` (UUID)
   - `project_id` (UUID, Foreign Key)
   - `result_file_url` (String, path to the output Excel/CSV)
   - `logs` (Text)
   - `executed_at` (Timestamp)

---

## 4. Core Features

### 4.1. Authentication
- Secure login and registration.
- Password hashing using `bcrypt`.
- Protected routes on the frontend ( তানStack Router `beforeLoad` or layout guards).

### 4.2. Project & History Management
- **Dashboard:** A central view where the engineer can see all their past projects, execution dates, and statuses.
- **Create Project:** Step-by-step wizard to initialize a new processing task.

### 4.3. Data Upload
- A clean drag-and-drop interface accepting `.xlsx` or `.csv` files.
- Ensures the engineer uploads the 5 required datasets:
  1. **Marker** (Geological markers/depths per well)
  2. **Well** (Well metadata)
  3. **Production** (Production history over time)
  4. **Completion** (Perforations and squeeze events)
  5. **Lumping** (Aggregated group data/sands)

### 4.4. Execution Engine (The "Auto Marker Machine")
- The core algorithm from `Markering and Splitting (GG v1).ipynb` will be refactored into clean FastAPI services.
- Translates the `squeeze_machine`, `classify_perf`, and marker lookups into efficient asynchronous background tasks (using `BackgroundTasks` in FastAPI or Celery/RQ if it takes longer than Cloudflare's timeout).
- Generates a final concatenated `pandas.DataFrame` and saves it as a downloadable report.

---

## 5. Development Phases

### Phase 1: Environment Setup
- Initialize Git repository.
- Setup monorepo structure (`/frontend` and `/backend`).
- Configure backend (FastAPI, Neon DB connection, Alembic).
- Configure frontend (Vite + React + TanStack Router + TailwindCSS + Shadcn UI).

### Phase 2: Backend Auth & Database
- Implement user models and DB migrations.
- Create `/auth/register` and `/auth/login` endpoints.
- Setup JWT issuance and validation middleware.

### Phase 3: Frontend Scaffolding & Auth UI
- Implement layout and routing (TanStack Router).
- Build Shadcn forms for Login and Registration.
- Build the main Dashboard (Projects List).

### Phase 4: Core Logic & Upload API
- Create AWS S3 (or local storage for MVP) integration to handle file uploads safely.
- Create API endpoints for Project creation and file uploading.
- **Data Engineering:** Port the Jupyter Notebook logic to Python modules (`services/engine.py`). Handle edge cases and optimize Pandas operations.

### Phase 5: Execution UI & Results
- Build the multi-step upload wizard in React.
- Add an "Execute" button that triggers the backend processing.
- Build a live loading/polling state (TanStack Query makes this trivial) to check processing status.
- Allow users to download the final calculated data.

### Phase 6: Deployment
- Deploy PostgreSQL database on **Neon**.
- Deploy FastAPI backend on **Railway**, setting environment variables.
- Deploy React Vite frontend on **Cloudflare Pages**.
- Final QA testing to ensure seamless execution.
