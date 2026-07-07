# Auto-Reviewer Agent for Deep Learning Papers

An automated reviewing agent for deep learning papers based on the Claude API. It follows the 10-stage workflow defined in `todo.txt` to generate structured review comments for a PDF paper.

## Pipeline

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/be7b9336-8b68-4992-97ba-16f40ea32744" />

Each stage passes the original PDF to the model as a **cached document block**. The model can use both the text content and page-level visual information from the PDF, including figures, tables, equations, and layout. The following stages reuse the same PDF input through prompt caching.

## Installation

Clone the repo and move into it:

```bash
git clone https://github.com/Agents4Academia-AI/auto-reviewer.git
cd auto-reviewer
```

Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
```

Install dependencies and set up the environment file:

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY
```

## Usage

```bash
python reviewer_agent.py /path/to/paper.pdf
```

Optional arguments:

```bash
# Customize the output directory
python reviewer_agent.py paper.pdf --out ./my_reviews

# Disable web search in Stage 4 to save tokens
python reviewer_agent.py paper.pdf --no-web-search

# Adjust effort level: low/medium/high/xhigh/max
python reviewer_agent.py paper.pdf --effort medium
```

## Output

The following files will be generated in the `--out` directory, which defaults to `./reviews`:

* `{paper}.review.json` — full structured output from all 10 stages, including token usage
* `{paper}.review.md` — final author-facing review in Markdown format

## Web App

A small website wraps the same pipeline so people can upload a PDF in the
browser, watch the 10 stages progress live, and read the rendered review. See
[PLAN.md](PLAN.md) for the design rationale.

It runs as **two processes** that share a SQLite database:

* a stateless **web** tier (FastAPI) that validates uploads and enqueues jobs, and
* a separate **worker** process that runs the pipeline.

This split is deliberate: it keeps the web tier holding no state, so scaling up
later means running more processes (and swapping SQLite → Postgres, local disk →
S3) without touching application code.

How to run:
```bash
# 1. terminal A — the web server
uvicorn web.app:app --reload

# 2. terminal B — the worker
python -m web.worker
```

Then open http://localhost:8000, upload a PDF, and watch it move
`queued → running → done`. Reviews are saved under `data/` (gitignored):
`data/uploads/<id>.pdf` and `data/reviews/<id>.{json,md}`.

For deployment, set `REVIEWER_SITE_PASSWORD` in `.env` to require a shared password. If left
blank, auth is disabled — convenient for local use.

The worker spends API budget per upload. Uploads are bounded by a page
limit, a size limit, and a queue-depth cap (see the config table below).

## Configuration

Environment variables / `.env`:

| Variable                     | Default             | Description                                       |
| ---------------------------- | ------------------- | ------------------------------------------------- |
| `ANTHROPIC_API_KEY`          | Required            | Anthropic API key                                 |
| `REVIEWER_MODEL`             | `claude-opus-4-7`   | Main reasoning model                              |
| `REVIEWER_FAST_MODEL`        | `claude-sonnet-4-6` | Reserved for possible lightweight subtasks        |
| `REVIEWER_SITE_PASSWORD`     | _(empty)_           | Web app shared password; blank disables auth      |
| `REVIEWER_SECRET_KEY`        | falls back to above | Secret for signing the session cookie             |
| `REVIEWER_DATA_DIR`          | `data`              | Where uploads, reviews, and the SQLite db live    |
| `REVIEWER_DB_URL`            | `sqlite:///…`       | SQLAlchemy URL (point at Postgres to scale out)   |
| `REVIEWER_MAX_PDF_PAGES`     | `60`                | Reject PDFs with more pages                        |
| `REVIEWER_MAX_UPLOAD_BYTES`  | `26214400` (25 MB)  | Reject larger uploads                             |
| `REVIEWER_MAX_QUEUE_DEPTH`   | `20`                | Reject uploads when this many jobs are queued     |
| `REVIEWER_MAX_REVIEWS_PER_USER` | `10`             | Per-user upload cap (queued/running/done count)   |
| `REVIEWER_MAX_TOTAL_REVIEWS` | `50`                | Site-wide cap across all users                    |
| `REVIEWER_WORKER_COUNT`      | `1`                 | Deployed worker-pool size; shown as workers free in the UI |

## File Structure

```text
config.py           - Configuration loading with dotenv
pdf_parser.py       - PDF → Claude document input, encoded as base64
prompts.py          - Prompt templates for the 10 stages
llm_client.py       - Anthropic SDK wrapper: caching + adaptive thinking + web_search
pipeline.py         - Connects the 10 stages and passes JSON context between them
reviewer_agent.py   - CLI entry point, including Markdown report rendering

web/                - Web app (upload site) around the same pipeline
  settings.py       - Web config: data paths, password, upload limits
  jobs.py           - SQLAlchemy job store; the jobs table doubles as the queue
  storage.py        - Storage interface + LocalStorage (disk) implementation
  progress.py       - Maps pipeline log lines to per-job stage progress
  worker.py         - Background process: claim job → run pipeline → save result
  auth.py           - Shared-password signed-cookie auth
  app.py            - FastAPI routes: upload, status API, pages, login
  templates/        - Jinja2 pages (index, review, login)
  static/           - app.js (polling + markdown render) and styles
```

## Known Limitations

* PDF input: The agent directly uses PDF document input from the Anthropic Messages API. The model analyzes both extracted text and page images, making it more suitable than local `pypdf`-based text extraction for papers with figures, tables, equations, and complex layouts.
* Request size / page count: The PDF must satisfy Anthropic API limits for document input. Very large papers or supplementary materials may need to be split.
* Novelty check depends on the retrieval quality of the `web_search` tool. For more reliable search, dedicated APIs such as Semantic Scholar or arXiv can be added.
* No parallelization: the 10 stages run strictly in sequence because they have dependencies.


## Suggested Next Steps

1. Write intermediate cache files for each stage to support checkpoint-based resume.
2. Integrate the Semantic Scholar API in Stage 4 for more accurate paper retrieval.
3. Add an automatic splitting strategy for long PDFs and supplementary materials.
4. Add a batch mode for multiple papers using the Anthropic Batches API.
