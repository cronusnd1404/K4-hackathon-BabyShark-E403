# VLearn Tutor+ frontend

React/Vite interface for repository-provided course PDFs. It lists documents from
the backend, renders them with `react-pdf`, shows background ingestion progress,
and enables summary/explanation/exercise actions when extraction is ready.

Users cannot upload PDFs. Available files come from:

- `codebase/prototype/backend/data/raw_pdfs`
- `data/vlearn-pack/slides`

## Run

```powershell
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

The backend defaults to `http://localhost:8020`. Override it with
`VITE_API_BASE_URL` when needed.

## Check

```powershell
npm.cmd run lint
npm.cmd run build
```
