# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:


## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
[new_code]
# DocXpress Frontend

React, TypeScript, and Vite interface for the local DocXpress FastAPI backend.

```powershell
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Set `VITE_API_BASE_URL` to point at the local backend when it is not running on the default `http://127.0.0.1:8000`.

The UI uses real backend responses for upload, analysis, structure detection, presets, formatting status, validation, comparison data, and DOCX download. It does not provide persistent history or rendered page previews because those capabilities are not exposed by the backend.
