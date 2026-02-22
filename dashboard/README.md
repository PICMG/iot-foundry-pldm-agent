# EW Demo Dashboard (React + TypeScript)

This dashboard provides a local frontend for driving Redfish mockup workflows against the Python mock server in this repository.

## Workflows Implemented

- Authentication workflow (SessionService call + local fallback mode)
- Chassis View from `/redfish/v1/Chassis` with `Status.State` visual indicators
- Automation View from `/redfish/v1/AutomationNodes` with `Status.State` visual indicators
- Read-only "Supported Actions" panels for selected resources with advertised actions
- Run-a-Job workflow using `JobService` + `JobDocuments` dynamic form generation
  - Parameter form generated from `ParameterMetadata`
  - Job submission posts to `JobService/Jobs`
  - First supported executor is updated via `Links.ExecutingJobs`
- Dynamic explorer (collection- and link-driven navigation without hard-coded member IDs)

## Prerequisites

- Node.js 20+
- npm 10+
- Python 3 + dependencies for `redfishMockupServer.py`

## Local Run

1. Start the mock server from repo root:

```bash
python3 redfishMockupServer.py -D iot-mockup -S -H 127.0.0.1 -p 8000
```

2. Start the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

3. Open:

- `http://127.0.0.1:5173`

## Base URL

The dashboard defaults to:

- `/redfish/v1` (proxied by Vite to `http://127.0.0.1:8000`)

You can override via:

- top-bar Base URL field
- or `VITE_REDFISH_BASE` in `.env`

## Test and Lint

```bash
npm test
npx eslint .
```

## Notes

- The mockup server supports `GET`, `PATCH`, `POST`, and `DELETE` for relevant resources. `PUT` returns `405` in current implementation.
- Browser CORS is handled in development through Vite proxy config for `/redfish`.
