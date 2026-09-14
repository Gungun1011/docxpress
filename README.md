# DocXpress

DocXpress is a local DOCX analysis and publication-formatting tool. It parses a manuscript into an immutable document AST, classifies structure with deterministic rules plus offline ML, applies configurable publication profiles, and verifies that text content was preserved before offering the formatted DOCX.

## Core Features

- Ordered DOCX parsing for paragraphs, headings, lists, tables, figures, captions, and references.
- Hybrid structure detection using regex rules, NLP features, offline scikit-learn models, and contextual smoothing.
- Formatting-only publication profiles, including the hackathon default, trade, academic, and fiction profiles.
- SHA-256 content verification with changed, missing, and added element reporting.
- Local FastAPI backend and React/Vite editorial interface.
- Sanitized uploads, isolated job directories, DOCX archive checks, and local-only CORS origins.

## Run Locally

Install Python dependencies:

```powershell
\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the backend:

```powershell
\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

During local Vite development, `VITE_API_BASE_URL` can point to the backend
and otherwise defaults to `http://127.0.0.1:8000`. Production builds use
same-origin relative API paths.

### CORS configuration

The backend always allows the local development origins
`http://localhost:5173` and `http://127.0.0.1:5173`. Additional origins can be
provided through the comma-separated `DOCXPRESS_CORS_ORIGINS` environment
variable when needed for local development.

The API does not enable credentialed CORS requests.

## Single-service Render deployment

The repository includes a multi-stage [Dockerfile](./Dockerfile) that builds
the Vite frontend and runs it from the same FastAPI Web Service. The container
serves the production UI at `/`, serves client-side routes with the SPA
fallback, and keeps `/api/*` requests routed to FastAPI.

Configure the Render service as a **Docker Web Service** using the repository
root as its context. The Dockerfile is required for a deterministic build
because it provides Node/npm for `npm ci` and `npm run build` before installing
and starting the Python application. Render does not need a separate build or
start command for Docker services; the Dockerfile runs the equivalent of:

```text
Build: docker build .
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `DOCXPRESS_CORS_ORIGINS` only if local development needs browser requests
from another origin. Production UI and API requests are same-origin and use
relative `/api/...` paths.

## Project Structure

```text
app/                 Python AST, parser, ML, formatter, and FastAPI backend
frontend/            React, TypeScript, and Vite editorial interface
tests/               Python parser, classifier, formatter, API, and preservation tests
sample_documents/    Deterministic DOCX fixtures for local testing
requirements.txt     Python dependencies
```

## Workflow

1. Upload a `.docx` manuscript.
2. Run the local parser and hybrid structure analysis.
3. Inspect returned element classifications and confidence values.
4. Select a backend publication profile.
5. Format the source into a separate output file.
6. Review the preservation report.
7. Download the formatted DOCX only after validation passes.

## Validation

The preservation service compares normalized ordered text sequences and SHA-256 hashes. It validates text content, not byte-level DOCX identity: formatting necessarily changes the DOCX package bytes. The UI therefore reports **Text content preserved** rather than “file unchanged.”

## Tests

```powershell
\.venv\Scripts\python.exe -m pytest -v
cd frontend
npm run lint
npm run build
```

Observed repository status at the final audit:

- Python suite: 84 passed, 3 pre-existing NLP failures.
- Frontend lint: passed.
- Frontend production build: passed.

## Privacy and Storage

Processing is local and does not call OpenAI, Gemini, cloud OCR, analytics, or telemetry services. Uploaded files are stored in `.docxpress_data` for the current process session and are isolated by generated document ID. Orphaned job directories are removed when a new service process starts. The API does not expose persistent document history.

## Known Limitations

- Job metadata is held in memory and is lost when the backend restarts.
- Rendered DOCX page previews are not exposed by the current backend; the comparison view uses returned ordered element data and preservation results.
- The 400-page-style benchmark completed with 4,000 elements, but broad 400+ page performance is not claimed as a universal guarantee.
- Three existing NLP feature tests currently fail around title-case, isolation, and an unstyled heading; these are unrelated to the API/frontend audit.

Observed benchmark on a generated 400-page-style workload: 4,000 elements, 17.426 seconds parsing, 0.371 seconds analysis, 21.837 seconds formatting plus validation, with preservation passing. This is an observed workload measurement, not a universal performance guarantee.
