# Auto-Reviewer Agent for Deep Learning Papers

An automated reviewing agent for deep learning papers based on the Claude API. It follows the 10-stage workflow defined in `todo.txt` to generate structured review comments for a PDF paper.

## Pipeline

| Stage | Goal                                                                                                        |
| ----- | ----------------------------------------------------------------------------------------------------------- |
| 0     | Directly read the PDF → structured paper representation: title, claims, contributions, figures/tables, etc. |
| 1     | Overall understanding: one-paragraph summary + claim-evidence map                                           |
| 2     | Section-by-section analysis: issues / missing information / ambiguous claims                                |
| 3     | Claim extraction and evidence mapping: categorized by novelty / correctness / empirical evidence, etc.      |
| 4     | Novelty check: use Claude’s built-in `web_search` tool to find similar prior work                           |
| 5     | Significance / impact analysis from multiple perspectives: 5 personas                                       |
| 6     | Rigor check: internal correctness, claim support, experimental rigor                                        |
| 7     | Review planning: strengths / weaknesses / recommendation                                                    |
| 8     | Draft review: author-facing review text                                                                     |
| 9     | Self-critique: identify hallucinations / overly strong claims / inconsistencies                             |
| 10    | Finalize: apply the critique and output the final review + improvement checklist                            |

Each stage passes the original PDF to the model as a **cached document block**. The model can use both the text content and page-level visual information from the PDF, including figures, tables, equations, and layout. The following stages reuse the same PDF input through prompt caching.

## Installation

```bash
cd /home/weiliu1/mypaper/2026/ai-scientist/githubcode
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

## Configuration

Environment variables / `.env`:

| Variable              | Default             | Description                                |
| --------------------- | ------------------- | ------------------------------------------ |
| `ANTHROPIC_API_KEY`   | Required            | Anthropic API key                          |
| `REVIEWER_MODEL`      | `claude-opus-4-7`   | Main reasoning model                       |
| `REVIEWER_FAST_MODEL` | `claude-sonnet-4-6` | Reserved for possible lightweight subtasks |

## File Structure

```text
config.py           - Configuration loading with dotenv
pdf_parser.py       - PDF → Claude document input, encoded as base64
prompts.py          - Prompt templates for the 10 stages
llm_client.py       - Anthropic SDK wrapper: caching + adaptive thinking + web_search
pipeline.py         - Connects the 10 stages and passes JSON context between them
reviewer_agent.py   - CLI entry point, including Markdown report rendering
```

## Known Limitations

* PDF input: The agent directly uses PDF document input from the Anthropic Messages API. The model analyzes both extracted text and page images, making it more suitable than local `pypdf`-based text extraction for papers with figures, tables, equations, and complex layouts.
* Request size / page count: The PDF must satisfy Anthropic API limits for document input. Very large papers or supplementary materials may need to be split.
* Novelty check depends on the retrieval quality of the `web_search` tool. For more reliable search, dedicated APIs such as Semantic Scholar or arXiv can be added.
* No parallelization: the 10 stages run strictly in sequence because they have dependencies.
* No persistent intermediate results: if the pipeline fails halfway, it must be rerun from the beginning.

## Suggested Next Steps

1. Write intermediate cache files for each stage to support checkpoint-based resume.
2. Integrate the Semantic Scholar API in Stage 4 for more accurate paper retrieval.
3. Add an automatic splitting strategy for long PDFs and supplementary materials.
4. Add a batch mode for multiple papers using the Anthropic Batches API.
