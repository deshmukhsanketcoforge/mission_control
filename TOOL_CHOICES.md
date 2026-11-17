# Tool choices


## Back end: FastAPI (Python 3.12, Pydantic v2, uv)

* **Why:** Pydantic validates every request and gives us field-level error messages
  for free. It also validates model replies against a schema, which the sorting step
  needs. `asyncio.gather` runs the three model checks at the same time. pytest makes
  the no-network tests simple.
* **Rejected:** Node with Express. It works, but we would add Zod and more glue to
  get the same validation, and the model SDK and test tooling are less direct for
  this job.
* **Customer concern:** The verdict must be auditable and deterministic. Plain,
  typed Python functions for the launch limits are easy to read and test, and a
  reviewer can check them without reading framework code.

## Front end: React + Vite + TypeScript

* **Why:** The console is a set of small interactive pieces (a form, a list, step
  cards, an approve button). React fits that. Vite starts fast and builds to static
  files, so FastAPI can serve them and the app runs as one process. TypeScript keeps
  the report shape the same on both sides of the API.
* **Rejected:** Next.js. Server rendering and file-based routing are not needed for
  an internal console, and it adds a second server to run.
* **Customer concern:** The Flight Director has no time to read raw messages. The UI
  must be fast and simple, with errors shown next to the field that caused them.

## Database: SQLite (SQLModel / SQLAlchemy)

* **Why:** Data is stored in a file, so reports survive a restart with nothing to
  install. One file also makes the restart test easy to write and to trust.
* **Rejected:** PostgreSQL. It is stronger for many users writing at once, but it
  needs a running service or Docker, which breaks the one-command start.
* **Customer concern:** Reports are safety records and must not be lost. Writes are
  committed before the API answers, and the file can be backed up by copying it. If
  Meridian needs many consoles at scale, SQLModel lets us move to PostgreSQL by
  changing the connection URL.

## Model: Anthropic Claude behind one interface

* **Why:** Small, fast Claude models are cheap and good at short structured tasks
  (sorting, checks). A stronger model writes and reviews the briefing. Structured
  output through tool use gives us JSON we can validate in code. All calls go
  through one `LLMClient` interface, so tests use a fake and need no API key.
* **Rejected:** One large model for every step. It would raise the cost per report
  and slow down each step, with no gain on short classification tasks.
* **Customer concern:** Cost per report and trust. Cost is calculated in code from
  token counts. Model output never decides the verdict, and a note that tries to
  give the system instructions is flagged and cannot change it.
