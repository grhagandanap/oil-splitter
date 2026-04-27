# Product Requirements Document (PRD): Oil Splitting Tools

## 1. Introduction
### 1.1 Purpose
The purpose of this document is to outline the requirements for building the **Oil Splitting Tools** web application. This application aims to automate and manage the process of calculating and allocating oil splits based on various field datasets.

### 1.2 Background
The core business logic for oil splitting currently exists as a Python script within a Jupyter Notebook (`Markering and Splitting.ipynb`). To make this tool accessible, scalable, and user-friendly, it needs to be converted into a full-stack web application.

## 2. Product Vision & Scope
### 2.1 Vision
To provide engineers and analysts with a fast, reliable, and easy-to-use web interface for computing oil splits, eliminating the need to manually run Python scripts and manage local environments.

### 2.2 Scope
- **In Scope:** 
  - User authentication and authorization (login, registration, secure JWT-based sessions).
  - Data ingestion for 5 specific dataset types (Marker, Well, Completion, Production, Lumping).
  - Data persistence and management using a relational database.
  - Execution of the core oil splitting algorithm via an API.
  - Interactive UI for uploading data, triggering calculations, and viewing results.
- **Out of Scope (for MVP):**
  - Advanced user role management (RBAC) beyond basic access.
  - Real-time collaborative editing of datasets.
  - Third-party integrations outside of the specified deployment environments.

## 3. Target Audience
- Petroleum Engineers
- Data Analysts
- Operations Managers

## 4. User Stories
1. **As a user**, I want to register and log in to the application securely so that my data and calculations remain private.
2. **As an engineer**, I want to upload my datasets (CSV/Excel) or paste them directly into the app so that I don't have to format files manually.
2. **As an analyst**, I want the system to validate my inputs (Marker, Well, Completion, Production, Lumping) before running the calculation to avoid runtime errors.
3. **As a user**, I want to click a button to run the oil splitting algorithm and see the results displayed in a clear, tabular format on the dashboard.
4. **As a user**, I want to view a history of my previous runs and their inputs/outputs so that I can audit past decisions.

## 5. Technical Requirements
### 5.1 Architecture
The system will follow a decoupled client-server architecture.

### 5.2 Technology Stack
- **Backend:** FastAPI (Python 3.10+)
- **Authentication:** JWT (JSON Web Tokens), `passlib` (for password hashing), `python-jose`
- **Database:** PostgreSQL (Containerized via Docker for local development)
- **ORM:** SQLAlchemy (with Alembic for migrations)
- **Frontend:** React.js initialized via Vite
- **Frontend Libraries:** TanStack Router (routing), TanStack Query (data fetching/state management), Tailwind CSS (styling)
- **Deployment:** 
  - Backend: FastAPI Cloud
  - Frontend: Cloudflare Workers / Cloudflare Pages

### 5.3 Data Requirements
The application must handle the following core entities (inputs for the algorithm):
1. **Marker Data:** Depths and specific marker names per well.
2. **Well Data:** General well identifiers.
3. **Completion Data:** Perforation and squeeze events with dates and depth for each well.
4. **Production Data:** Monthly or daily production volumes (Oil, Gas, Water, Water Injection).
5. **Lumping Data:** Grouping or aggregation KH (permeability and thickness) for the allocation factor.

## 6. Functional Requirements
### 6.1 Data Ingestion
- The frontend must provide forms/interfaces to upload files (CSV/XLSX) for each of the 5 input types.
- Support for copy-pasting data directly from Excel into a web grid.
- Backend endpoints must parse and validate incoming data structures before saving to the database.

### 6.2 Processing
- A dedicated execution endpoint (`POST /api/v1/split/run`) that reads the stored datasets for a specific project/run, executes the ported Python logic, and saves the output.

### 6.3 Results & Reporting
- The UI must display the resulting split allocation.
- Allow users to export the final results back to CSV or Excel.

## 7. UI/UX Guidelines
- **Clean & Minimalist:** Focus on data visibility. Use data grids (e.g., TanStack Table) for rendering large sets of input and output data.
- **Feedback:** Provide clear loading states, success toasts, and detailed error messages (especially for data validation failures).
- **Navigation:** Simple top or side navigation to switch between "Data Inputs", "Run Calculation", and "History".

## 8. Deployment & DevOps
- Provide a `docker-compose.yml` for local development that spins up the PostgreSQL database.
- Backend must be packaged properly with `requirements.txt` or `pyproject.toml` for FastAPI Cloud deployment.
- Frontend must include a build script (`pnpm run build`) optimized for Cloudflare Pages.

## 9. Success Metrics
- Successful translation of the Jupyter Notebook logic to a FastAPI service with 100% accuracy on sample datasets.
- Sub-2 second load times for the frontend application.
- End-to-end execution of the splitting process via the web UI without manual intervention.