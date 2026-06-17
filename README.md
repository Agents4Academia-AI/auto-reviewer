# Auto-Reviewer Agent (Deep Learning Papers)

An automated review agent for deep learning papers powered by the Claude API. It follows the 10-stage workflow defined in `todo.txt` to generate structured review feedback for a given PDF paper.

## Pipeline

| Stage | Objective                                                                                             |
| ----- | ----------------------------------------------------------------------------------------------------- |
| 0     | Parse PDF → structured paper representation (`title`, `claims`, `contributions`, etc.)                |
| 1     | Overall understanding: one-paragraph summary + claim-evidence map                                     |
| 2     | Section-by-section analysis: issues / missing information / ambiguous claims                          |
| 3     | Claim extraction and evidence mapping, categorized by novelty / correctness / empirical support, etc. |
| 4     | Novelty check: use Claude’s built-in `web_search` tool to find similar prior work                     |
| 5     | Multi-perspective significance / impact analysis using 5 personas                                     |
| 6     | Rigor check: internal correctness, claim support, and experimental rigor                              |
| 7     | Review planning: strengths / weaknesses / recommendation                                              |
| 8     | Draft review: author-facing review text                                                               |
| 9     | Self-critique: identify hallucinations, overly strong claims, and inconsistencies                     |
| 10    | Finalize: apply critique and output the final review + improvement checklist                          |

The full paper text is reused across stages via **prompt caching**. The full paper is written to the cache only in the first stage, while the remaining 9 stages use low-cost cache reads.

## Installation

```bash
cd /home/weiliu1/mypaper/2026/ai-scientist/githubcode
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

```bash
python reviewer_agent.py /path/to/paper.pdf
```

Optional arguments:

```bash
# Specify a custom output directory
python reviewer_agent.py paper.pdf --out ./my_reviews

# Disable web search in Stage 4 to save tokens
python reviewer_agent.py paper.pdf --no-web-search

# Adjust effort level: low/medium/high/xhigh/max
python reviewer_agent.py paper.pdf --effort medium
```

## Output

The following files will be generated under the `--out` directory, which defaults to `./reviews`:

* `{paper}.review.json` — complete structured outputs from all 10 stages, including token usage
* `{paper}.review.md` — final author-facing review in Markdown format

## Configuration

Environment variables / `.env`:

| Variable              | Default             | Description                                 |
| --------------------- | ------------------- | ------------------------------------------- |
| `ANTHROPIC_API_KEY`   | Required            | Anthropic API key                           |
| `REVIEWER_MODEL`      | `claude-opus-4-7`   | Main reasoning model                        |
| `REVIEWER_FAST_MODEL` | `claude-sonnet-4-6` | Reserved for potential lightweight subtasks |

## File Structure

```text
config.py           - Configuration loading via dotenv
pdf_parser.py       - PDF → plain text using pypdf
prompts.py          - Prompt templates for the 10 stages
llm_client.py       - Anthropic SDK wrapper with caching, adaptive thinking, and web_search
pipeline.py         - Runs the 10-stage pipeline and passes JSON context across stages
reviewer_agent.py   - CLI entry point, including Markdown report rendering
```

## Known Limitations: Basic Version

* PDF text extraction uses `pypdf`, which may perform poorly on scanned papers or papers with complex layouts. This can later be replaced with `pymupdf` or Claude’s native PDF input capability by passing the PDF directly as base64.
* Figures and equations are currently only extracted as short descriptions; no visual understanding is performed. To support this, the pipeline can be modified to pass PDF page images directly to Claude’s multimodal interface.
* The novelty check depends on the retrieval quality of the `web_search` tool. Dedicated APIs such as Semantic Scholar or arXiv can be added for more reliable literature search.
* The pipeline is not parallelized. All 10 stages run strictly sequentially because later stages depend on earlier outputs.
* Intermediate results are not persisted. If the process fails midway, it currently needs to be restarted from the beginning.

## Suggested Next Steps

1. Pass PDFs directly to Claude instead of relying on plain text extracted by `pypdf`, preserving layout and enabling better figure/table understanding.
2. Integrate the Semantic Scholar API into Stage 4 for more precise paper retrieval.
3. Write intermediate cache files for each stage to support checkpointing and resume-on-failure.
4. Add multi-paper batch mode using the Anthropic Batches API to reduce costs by half.
