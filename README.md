# ToDo Backend API

Complete backend for a To Do list web application using FastAPI, SQLAlchemy, and SQLite (`todo_app.db`).

## Features
- CRUD API for todos
- Email/password sign-up and sign-in
- Project creation with multiple collaborators
- Task assignment to multiple users and optional project links
- Priority support (`low`, `medium`, `high`)
- Due date, completion status, and full text search
- Filtering, sorting, and pagination
- Stats endpoint for dashboard cards
- CORS support for frontend integration
- Interactive dynamic frontend (`frontend/`) with auth, projects, and shared task assignment
- Pytest test suite

## Project Structure

```
app/
  api/
    routes/
      todos.py
  core/
    config.py
    database.py
  models/
    todo.py
  schemas/
    todo.py
  services/
    todo_service.py
  main.py
tests/
  test_todos.py
requirements.txt
.env.example
frontend/
  index.html
  styles.css
  app.js
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` (optional).

4. Start the API server:

```bash
uvicorn app.main:app --reload
```

API docs:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Run Frontend

The frontend is a dynamic single-page app in `frontend/` that consumes backend APIs.

1. Keep backend running at `http://127.0.0.1:8000`.
2. In a new terminal:

```bash
cd frontend
python -m http.server 3000
```

3. Open `http://127.0.0.1:3000`.
4. If needed, update the API base URL from the top-right input in the UI.

Frontend features:
- Create, edit, complete/uncomplete, and delete tasks
- Search, status and priority filters
- Sorting and manual refresh
- Live stats cards

## Run Tests

```bash
pytest -q
```

## API Endpoints

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/users`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/members`
- `DELETE /api/v1/projects/{project_id}/members/{member_id}`
- `POST /api/v1/todos`
- `GET /api/v1/todos`
- `GET /api/v1/todos/{todo_id}`
- `PATCH /api/v1/todos/{todo_id}`
- `DELETE /api/v1/todos/{todo_id}`
- `GET /api/v1/todos/stats`

### Query Params for `GET /api/v1/todos`
- `skip` (default: 0)
- `limit` (default: 20, max: 100)
- `completed` (`true` or `false`)
- `priority` (`low`, `medium`, `high`)
- `search` (title/description contains)
- `project_id`
- `sort_by` (`title`, `created_at`, `updated_at`, `due_date`)
- `sort_order` (`asc`, `desc`)

## Frontend Workflow

- Register or sign in from the landing screen.
- Create a shared project and select collaborators.
- Create tasks, optionally attach them to a project, and assign multiple users.
- Use the filter bar to narrow tasks by status, priority, and project.
