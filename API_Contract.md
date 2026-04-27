# API Contract: Oil Splitting Tools

This document outlines the RESTful API endpoints for the Oil Splitting Tools application. All endpoints under `/api/v1` are prefixed with the base URL. All protected endpoints require a valid JWT token in the `Authorization: Bearer <token>` header.

---

## 1. Authentication
### 1.1 Register User
- **Endpoint:** `POST /api/v1/auth/register`
- **Description:** Register a new user.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2026-04-27T00:00:00Z"
  }
  ```

### 1.2 Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Description:** Authenticate a user and receive JWT tokens.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR...",
    "token_type": "bearer"
  }
  ```

### 1.3 Get Current User
- **Endpoint:** `GET /api/v1/auth/me`
- **Description:** Get the authenticated user's details. Requires Authentication.
- **Response:** `200 OK`
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2026-04-27T00:00:00Z"
  }
  ```

---

## 2. Projects
Projects serve as containers for grouping related input datasets and their corresponding calculation runs.

### 2.1 Create Project
- **Endpoint:** `POST /api/v1/projects`
- **Description:** Create a new project. Requires Authentication.
- **Request Body:**
  ```json
  {
    "name": "Field Alpha Q1 Analysis",
    "description": "Oil splitting analysis for Field Alpha, Q1 2026."
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "id": 101,
    "owner_id": 1,
    "name": "Field Alpha Q1 Analysis",
    "description": "Oil splitting analysis for Field Alpha, Q1 2026.",
    "created_at": "2026-04-27T00:00:00Z",
    "updated_at": "2026-04-27T00:00:00Z"
  }
  ```

### 2.2 List Projects
- **Endpoint:** `GET /api/v1/projects`
- **Description:** List all projects owned by the authenticated user. Requires Authentication.
- **Response:** `200 OK` (Array of Project objects)

### 2.3 Get Project Details
- **Endpoint:** `GET /api/v1/projects/{project_id}`
- **Description:** Retrieve a specific project. Requires Authentication.
- **Response:** `200 OK` (Project object)

---

## 3. Data Ingestion (Datasets)
Endpoints to upload and manage the 5 input dataset types: `marker`, `well`, `completion`, `production`, `lumping`.

### 3.1 Upload Dataset (File)
- **Endpoint:** `POST /api/v1/projects/{project_id}/datasets/upload`
- **Description:** Upload a CSV or Excel file for a specific dataset type. Requires Authentication.
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `file`: The file to upload (.csv, .xlsx, .xls).
  - `kind`: The dataset kind (e.g., "marker", "well").
  - `sheet_name` (optional): Specific sheet name if Excel.
- **Response:** `201 Created`
  ```json
  {
    "id": 201,
    "project_id": 101,
    "kind": "marker",
    "source": "csv",
    "filename": "markers_q1.csv",
    "row_count": 50,
    "is_valid": true,
    "validation_errors": [],
    "created_at": "2026-04-27T00:00:00Z"
  }
  ```

### 3.2 Paste Dataset (JSON)
- **Endpoint:** `POST /api/v1/projects/{project_id}/datasets/paste`
- **Description:** Submit dataset rows directly via JSON (from pasted TSV/CSV data). Requires Authentication.
- **Request Body:**
  ```json
  {
    "kind": "marker",
    "data": [
      { "Well": "W-01", "Marker": "S1", "Depth": 1000 },
      { "Well": "W-01", "Marker": "S2", "Depth": 1500 }
    ]
  }
  ```
- **Response:** `201 Created` (Dataset preview object)

### 3.3 List Datasets
- **Endpoint:** `GET /api/v1/projects/{project_id}/datasets`
- **Description:** List all datasets uploaded to a project. Requires Authentication.
- **Query Parameters:** `kind` (optional) - Filter by dataset kind.
- **Response:** `200 OK` (Array of Dataset objects)

---

## 4. Execution & Results
Endpoints to trigger the oil splitting algorithm.

### 4.1 Run Oil Splitting Calculation
- **Endpoint:** `POST /api/v1/projects/{project_id}/split/run`
- **Description:** Execute the oil splitting logic using the valid datasets associated with the project. Requires Authentication.
- **Request Body:** (Optional configuration parameters)
  ```json
  {
    "first_marker_tolerance_ft": 5.0,
    "auto_middle_strategy": "ffill"
  }
  ```
- **Response:** `200 OK` or `201 Created`
  ```json
  {
    "run_id": 301,
    "project_id": 101,
    "status": "completed",
    "warnings": [],
    "summary": [
      {
        "Sand": "S1",
        "Total Oil": 1500.5,
        "Total Gas": 500.2,
        "Total Water": 200.0,
        "Total Water Injection": 0.0
      }
    ],
    "created_at": "2026-04-27T00:05:00Z"
  }
  ```

### 4.2 Get Run Results Detail
- **Endpoint:** `GET /api/v1/projects/{project_id}/split/runs/{run_id}`
- **Description:** Retrieve the detailed output of a specific calculation run, suitable for grid rendering or CSV export. Requires Authentication.
- **Response:** `200 OK` (Array of detailed output rows)
