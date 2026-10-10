# grad-checker

## Task Runner Commands

Run these commands from the repository root. Use either Go Task
(`Taskfile.yml`) or Make (`Makefile`); both provide the same commands.

| Operation | Task | Make |
| --- | --- | --- |
| List commands | `task` | `make` |
| Install all dependencies | `task setup` | `make setup` |
| Install frontend dependencies | `task frontend-install` | `make frontend-install` |
| Install backend dependencies | `task backend-install` | `make backend-install` |
| Start frontend development server | `task dev` | `make dev` |
| Build frontend | `task build` | `make build` |
| Preview frontend build | `task preview` | `make preview` |

Install dependencies before starting development or building, and run `build`
before `preview`. Backend setup requires uv and uses `backend/uv.lock` with
`uv sync --locked`. Backend server and test commands will be added when their
entry point and tests are implemented.

## Frontend Development Environment

The frontend uses Vite for HTML, CSS, and JavaScript development. The UI
framework, screens, application logic, and API integration are not implemented.
The HTML entry point is intentionally blank.

### Prerequisites

- Node.js: 20.19+ in the 20.x series, or 22.12+ (Vite requirement).
- npm: 11.12.1 was used to generate the lock file.
- Verified locally with Node.js 25.9.0 and npm 11.12.1.

### Setup

Run from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

The development URL is printed in the terminal (normally
http://127.0.0.1:5173). An empty page is expected until implementation starts.

On Windows PowerShell, use `npm.cmd` instead of `npm` if the execution policy
blocks `npm.ps1`:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

### Build and Preview

```sh
npm run build
npm run preview
```

Build artifacts are written to `frontend/dist/` and excluded from Git.
Commit `frontend/package-lock.json` when updating dependencies and use `npm ci`
to reproduce the installed versions.

Reference: [Vite Getting Started](https://vite.dev/guide/).
