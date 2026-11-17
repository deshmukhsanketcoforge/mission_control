# Mission Control: Go/No-Go Launch Console

A full stack web app for the last 90 minutes before a launch. Engineers at the consoles
file free-text anomaly reports. A pipeline reads and sorts each one, checks the readings
against the launch limits, and drafts a short briefing. The Flight Director reviews it and
is the only one who can approve it.

> **Status:** in active development. Report filing, the launch-limit checks, brief-by time
> and model sorting are done. The checks, draft and review loop, approval and Flight Director
> console are planned. See [Roadmap](#roadmap).

## Table of contents

- [Overview](#overview)
- [Quick start](#quick-start)
- [Running the tests](#running-the-tests)
- [Configuration](#configuration)
- [Development mode](#development-mode)
- [Tech stack](#tech-stack)
- [API](#api)
- [Input rules](#input-rules)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

## Overview

An engineer files a report with:

| Field | Type | Description |
|---|---|---|
| `name` | text | Who is filing the report |
| `station` | text | Console or station the report comes from |
| `wind_knots` | number | Wind speed reading |
| `temp_c` | number | Temperature reading, in degrees Celsius |
| `fuel_pct` | number | Fuel reading, in percent |
| `note` | text | Free-text description of the anomaly |

### Planned pipeline

| Step | Done by | Rule |
|---|---|---|
| Sort by subsystem and severity | Model | Reply is checked against a schema. An invalid value falls back safely. |
| Check the launch limits and set the verdict | **Plain code, never a model** | Wind 25 knots or less, temperature 4 C or more, fuel 98 to 100 percent. Any reading outside its limit makes the verdict `no_go`. |
| Set the brief-by time | Plain code | 5, 15 or 30 minutes for high, medium or low severity. Any limit violation counts as high. |
| Run three checks at the same time | Model | Hidden instructions in the note, missing details, panic in the tone. A note that tries to instruct the system is flagged and never changes the verdict. |
| Draft and review the briefing | Model | A second call reviews the draft. Repeats for up to three rounds. |
| Approve | **A person** | Only the Flight Director can approve a briefing. |

The Flight Director console will show the reports, the briefing, the verdict, the cost and a
trace of each step.

## Quick start

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | any recent | Installs Python 3.12+ and the backend dependencies |
| [Node.js](https://nodejs.org/) and npm | Node 20+ | Builds the frontend |
| make | any | Runs the commands below |

No API key and no database server are needed.

### Start the app

```bash
make start
```

This installs the frontend dependencies, builds the React app, and starts FastAPI, which serves
both the API and the built frontend. Then open **http://localhost:8000**.

To use another port:

```bash
make start PORT=9000
```

Reports are saved in `data/mission_control.db` and are still there after a restart.

## Running the tests

```bash
make test
```

This runs the backend tests (pytest) and then the frontend tests (Vitest). The tests need no
network and no API key. Once the model pipeline lands, all model calls will go through one
interface with a fake client, so the tests will stay offline.

A test guard blocks all network connections and removes API keys from the environment, so
a test that tries to reach a real model fails instead of passing by accident.

What the tests cover today:

- **Launch limits:** each limit is tested exactly on the limit and just past it (wind 25 and
  25.01, temperature 4 and 3.99, fuel 98, 97.99, 100 and 100.01). Readings that are not
  finite numbers count as violations.
- **Brief-by time:** 5, 15 and 30 minutes for high, medium and low. Any violation gives 5.
- **Model sorting:** a valid reply is used. Invalid values, wrong case, missing fields, text
  that is not JSON and a failed call all fall back to `unknown` / `high`.
- **Model interface:** the fake client and the Anthropic client (against a stub SDK).
- Filing a report saves every field.
- Missing, blank, non-numeric, out-of-range and too-long input is rejected with a clear message
  and nothing is saved.
- Reports are still there after the app restarts (a new app on the same database file).
- The form sends every field, shows errors next to the field they belong to, and does not call
  the API when a required field is empty.

## Configuration

| Setting | Default | Purpose |
|---|---|---|
| `PORT` (make variable) | `8000` | Port for `make start` |
| `MISSION_CONTROL_DB_URL` (environment variable) | `sqlite:///<repo>/data/mission_control.db` | Database location. Point it at another SQLite file, for example `sqlite:////tmp/demo.db`. |

Settings can also live in a `.env` file, which `make start` reads when it exists:

```bash
cp .env.example .env     # then edit it. .env is ignored by git.
```

`.env.example` lists every setting. `ANTHROPIC_API_KEY` is only needed for live model calls
from SAN-11 on. The app and the tests run without it. Use plain `KEY=value` lines, without
quotes.

To start from a clean slate, stop the app and delete the `data/` folder.

## Development mode

For live reload, run the backend and frontend in two terminals:

```bash
# Terminal 1: backend on http://127.0.0.1:8000
cd backend && uv run uvicorn app.main:app_factory --factory --reload

# Terminal 2: frontend on http://localhost:5173 (proxies /api to the backend)
cd frontend && npm install && npm run dev
```

Other useful commands:

```bash
cd backend && uv run pytest -q          # backend tests only
cd frontend && npm test                 # frontend tests only
cd frontend && npm run build            # production build into frontend/dist
```

## Tech stack

| Layer | Choice |
|---|---|
| Back end | FastAPI, Python 3.12+, Pydantic v2, managed with uv |
| Front end | React, Vite, TypeScript, tested with Vitest and Testing Library |
| Database | SQLite through SQLModel and SQLAlchemy |
| Models | Anthropic Claude (Haiku for sorting, Sonnet for drafting) behind a single interface, with a fake for tests |

The reason for each choice, the alternative we rejected and the customer concern it answers are
in [TOOL_CHOICES.md](TOOL_CHOICES.md).

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reports` | File a report. Returns `201` and the saved report. Returns `422` on bad input. |
| `GET` | `/api/reports` | List reports, newest first. |
| `GET` | `/api/health` | Health check. |

Example:

```bash
curl -X POST http://localhost:8000/api/reports \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Ada Lovelace",
    "station": "Propulsion-2",
    "wind_knots": 12.5,
    "temp_c": 18,
    "fuel_pct": 99.2,
    "note": "Valve V3 stuck for two seconds before opening."
  }'
```

A rejected report returns one message per field:

```json
{ "errors": { "fuel_pct": "Fuel must be between 0 and 100 percent." } }
```

## Input rules

These rules reject impossible input, such as typos and wrong units. They are not the launch
limits. A reading that breaks a launch limit is still accepted and filed. The launch-limit check
(planned) will mark it `no_go`.

| Field | Rule |
|---|---|
| `name`, `station` | Required, 1 to 100 characters after trimming spaces |
| `note` | Required, 1 to 2000 characters after trimming spaces |
| `wind_knots` | Number from 0 to 200 |
| `temp_c` | Number from -90 to 60 |
| `fuel_pct` | Number from 0 to 100 |

## Project structure

```
mission_control/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app, routes, error format, serves the frontend
│   │   ├── models.py      # Database tables
│   │   ├── schemas.py     # Request and response shapes, input validation
│   │   ├── db.py          # Database connection
│   │   ├── domain/        # Plain code, no model: limits.py, brief_time.py
│   │   ├── llm/           # base.py (the one interface), anthropic_client.py, fake.py
│   │   └── pipeline/      # sort.py (model sorting with checked reply), prompts.py
│   └── tests/             # pytest tests
├── frontend/
│   └── src/
│       ├── App.tsx            # Page layout
│       ├── ReportForm.tsx     # Filing form
│       ├── ReportList.tsx     # Filed reports
│       ├── api.ts             # API calls
│       └── *.test.tsx         # Vitest tests
├── .env.example               # Settings template, copy to .env
├── Makefile                   # make start, make test
└── TOOL_CHOICES.md            # Why each tool was chosen
```

## Roadmap

Work is tracked in the Linear project **Mission control**. Each ticket ships as one pull request.

| Ticket | Scope | Status |
|---|---|---|
| SAN-9 | Scaffold, report filing, restart test, tool choices, README | Done |
| SAN-10 | Launch limits, brief-by time, model interface with a fake, model sorting | Done |
| SAN-11 | Three checks, draft and review loop, human-only approval, trace and cost | Planned |
| SAN-12 | Flight Director console, final docs | Planned |

## Documentation

- [TOOL_CHOICES.md](TOOL_CHOICES.md): tool choices with reasons, rejected alternatives and customer concerns
