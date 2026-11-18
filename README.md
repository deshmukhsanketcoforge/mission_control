# Mission Control: Go/No-Go Launch Console

A full stack web app for the last 90 minutes before a launch. Engineers at the consoles
file free-text anomaly reports. A pipeline reads and sorts each one, checks the readings
against the launch limits, and drafts a short briefing. The Flight Director reviews it and
is the only one who can approve it.

## Table of contents

- [Quick start](#quick-start)
- [Running the tests](#running-the-tests)
- [Try it with sample data](#try-it-with-sample-data)
- [How it works](#how-it-works)
- [Using the console](#using-the-console)
- [Configuration](#configuration)
- [Development mode](#development-mode)
- [Tech stack](#tech-stack)
- [API](#api)
- [Input rules](#input-rules)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

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
network and no API key: every model call goes through one interface, and the tests use a fake.
A test guard blocks all network connections and removes API keys from the environment, so a
test that tries to reach a real model fails instead of passing by accident.

A saved run of both commands is in [docs/test-output.txt](docs/test-output.txt).

What the tests cover:

| Area | What is checked |
|---|---|
| Filing reports | Every field is saved. Missing, blank, non-numeric, out-of-range and too-long input is rejected with a clear message and nothing is saved. The form sends every field and shows each error next to its field. |
| After a restart | Reports, analysis and trace are still there when a new app opens the same database file. A report cut off mid-run is marked failed. |
| Launch limits | Each limit is tested exactly on the limit and just past it (wind 25 and 25.01, temperature 4 and 3.99, fuel 98, 97.99, 100 and 100.01). A reading that is not a finite number counts as a violation. |
| Brief-by time | 5, 15 and 30 minutes for high, medium and low. Any violation gives 5. |
| Sorting | A valid reply is used. Invalid values, wrong case, missing fields, text that is not JSON and a failed call all fall back to `unknown` / `high`. |
| Three checks | They run at the same time (the fake counts calls in flight). A check that fails or returns an invalid reply is flagged, not passed. |
| Hidden instructions | A note that gives instructions is flagged, sent to review, briefed as high, and never changes the verdict. |
| Draft and review loop | Stops at three rounds. Reviewer feedback goes into the next draft. A broken review never approves. |
| Approval | Only a person can approve. A state-machine test and a source scan show the pipeline cannot. Approving twice, approving a failed report or approving without a name is refused. |
| Trace and cost | One trace row per step with tokens. Cost per step and per report is calculated in code from a price table, checked to the digit. |
| Console | One trace card per step with its tokens, the cost exactly as the server calculated it, the verdict, the briefing, the review banner, and an approve button that needs a name and cannot be double-clicked. |

## Try it with sample data

With the app running (`make start` in one terminal), in another terminal:

```bash
make seed
```

This files eight sample reports: a clean go, each limit broken, readings exactly on the limits
and just past them, a note that tries to give the system instructions, and a panicked note.
Nothing is approved by seeding. Run it on an empty database: it skips a database that already
has reports (use `cd backend && uv run python -m app.seed --force` to add them anyway).

Then open the app and choose **Flight Director**.

## How it works

An engineer files a report:

| Field | Type | Description |
|---|---|---|
| `name` | text | Who is filing the report |
| `station` | text | Console or station the report comes from |
| `wind_knots` | number | Wind speed reading |
| `temp_c` | number | Temperature reading, in degrees Celsius |
| `fuel_pct` | number | Fuel reading, in percent |
| `note` | text | Free-text description of the anomaly |

| Step | Done by | Rule |
|---|---|---|
| Sort by subsystem and severity | Model | Reply is checked against a schema. An invalid value falls back safely. |
| Check the launch limits and set the verdict | **Plain code, never a model** | Wind 25 knots or less, temperature 4 C or more, fuel 98 to 100 percent. Any reading outside its limit makes the verdict `no_go`. |
| Set the brief-by time | Plain code | 5, 15 or 30 minutes for high, medium or low severity. Any limit violation counts as high. |
| Run three checks at the same time | Model | Hidden instructions in the note, missing details, panic in the tone. A note that tries to instruct the system is flagged and never changes the verdict. |
| Draft and review the briefing | Model | A second call reviews the draft. Repeats for up to three rounds. Reviewer feedback goes into the next draft. |
| Approve | **A person** | Only a person can approve a briefing. The pipeline stops at `pending_approval`. |

When a report is filed, the verdict and violations are saved straight away from plain code. The
model steps then run in the background. Each step is written to a trace with its model, tokens,
time and cost. Cost is calculated in code from the token counts.

A report is **sent to review** when the note tries to give instructions, a check could not be
completed, sorting fell back, or the reviewer never approved the draft. A note that gives
instructions is flagged, its severity is not trusted (the report is briefed as high), and it
never changes the verdict.

Report status: `processing` -> `pending_approval` -> `approved` (a person only), or `failed`.

## Using the console

Switch views at the top right.

**Engineer** is for filing. The form sends all six fields and shows each error next to its field.
Filed reports appear beside it with their verdict and status, and update on their own.

**Flight Director** is for reviewing:

- The list shows every report with its verdict, status, brief-by time and cost. It refreshes every
  two seconds and shows how many briefings are waiting for a decision.
- Open a report to see the verdict and each limit violation, the briefing, the original note, the
  three checks and the total cost.
- A yellow **Needs your review** banner says why a report was sent to review.
- The **trace** has one card per step, in order, with its model (or "plain code"), tokens, time and
  cost. A draft that was revised shows a card for every round.
- To approve, type your name and press **Approve briefing**. Only a pending briefing can be
  approved, and only by this button. Nothing in the pipeline approves.

## Configuration

| Setting | Default | Purpose |
|---|---|---|
| `PORT` (make variable) | `8000` | Port for `make start` and `make seed` |
| `MISSION_CONTROL_DB_URL` (environment variable) | `sqlite:///<repo>/data/mission_control.db` | Database location. Point it at another SQLite file, for example `sqlite:////tmp/demo.db`. |

Settings can also live in a `.env` file, which `make start` reads when it exists:

```bash
cp .env.example .env     # then edit it. .env is ignored by git.
```

`.env.example` lists every setting. With `ANTHROPIC_API_KEY` set, the pipeline calls Claude
(Haiku for sorting and checks, Sonnet for drafting and review). **Without a key the app runs in
demo mode:** an offline client with simple rules, which costs nothing and writes a briefing
labelled as a demo. The tests never use a key. Use plain `KEY=value` lines, without quotes.

To start from a clean slate, stop the app and delete the `data/` folder. Do not delete it while
the app is processing a report.

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
cd frontend && npm run lint             # lint the frontend
cd frontend && npm run build            # production build into frontend/dist
```

## Tech stack

| Layer | Choice |
|---|---|
| Back end | FastAPI, Python 3.12+, Pydantic v2, managed with uv |
| Front end | React, Vite, TypeScript, tested with Vitest and Testing Library |
| Database | SQLite through SQLModel and SQLAlchemy |
| Models | Anthropic Claude (Haiku for sorting and checks, Sonnet for drafting and review) behind a single interface, with a fake for tests |

The reason for each choice, the alternative we rejected and the customer concern it answers are
in [TOOL_CHOICES.md](TOOL_CHOICES.md).

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reports` | File a report. Returns `201` and the saved report. Returns `422` on bad input. |
| `GET` | `/api/reports` | List reports, newest first, with status, verdict, brief-by time, review flag and cost. |
| `GET` | `/api/reports/{id}` | One report with its analysis (verdict, violations, subsystem, severity, checks, briefing, cost) and the trace, one entry per step. |
| `POST` | `/api/reports/{id}/approve` | A person approves a pending briefing. Body: `{"approved_by": "Name"}`. Returns `409` if the report is not pending approval, `422` without a name. |
| `GET` | `/api/health` | Health check. |

Filing returns right away. The pipeline runs in the background, so poll `GET /api/reports/{id}`
until `analysis.status` is no longer `processing`.

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
limits. A reading that breaks a launch limit is still accepted and filed, and the launch-limit
check marks it `no_go`.

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
│   │   ├── main.py        # Creates the app and serves the frontend
│   │   ├── api/           # Routes: reports.py (file, list, detail, approve), health.py, errors.py
│   │   ├── services.py    # File a report, approve it (people only), recover after a restart
│   │   ├── domain/        # Plain code, no model: limits, brief_time, pricing, status
│   │   ├── llm/           # base (the one interface), anthropic_client, fake, demo, recording, factory
│   │   ├── pipeline/      # sort, checks, briefing_loop, runner, prompts
│   │   ├── models.py      # Database tables
│   │   ├── schemas.py     # Request and response shapes, input validation
│   │   ├── db.py          # Database connection
│   │   └── seed.py        # Sample reports for make seed
│   └── tests/             # pytest tests
├── frontend/
│   └── src/
│       ├── App.tsx            # Engineer / Flight Director switch
│       ├── ReportForm.tsx     # Filing form
│       ├── ReportList.tsx     # Filed reports (engineer view)
│       ├── Console.tsx        # Flight Director console: report list and detail pane
│       ├── ReportDetail.tsx   # Verdict, briefing, review banner, approve button
│       ├── TraceTimeline.tsx  # One TraceCard per step
│       ├── TraceCard.tsx      # Model, tokens, time and cost of one step
│       ├── CostBadge.tsx, VerdictBadge.tsx
│       ├── hooks.ts           # Polling for the list and the open report
│       ├── api.ts, format.ts  # API calls and display helpers
│       └── *.test.ts(x)       # Vitest tests
├── docs/test-output.txt       # Saved run of make test
├── .env.example               # Settings template, copy to .env
├── Makefile                   # make start, make test, make seed
└── TOOL_CHOICES.md            # Why each tool was chosen
```

## Roadmap

Work is tracked in the Linear project **Mission control**. Each ticket ships as one pull request.

| Ticket | Scope | Status |
|---|---|---|
| SAN-9 | Scaffold, report filing, restart test, tool choices, README | Done |
| SAN-10 | Launch limits, brief-by time, model interface with a fake, model sorting | Done |
| SAN-11 | Three checks, draft and review loop, human-only approval, trace and cost | Done |
| SAN-12 | Flight Director console, sample data, final docs | Done |

## Documentation

- [TOOL_CHOICES.md](TOOL_CHOICES.md): tool choices with reasons, rejected alternatives and customer concerns
- [docs/test-output.txt](docs/test-output.txt): saved output of `make test`
