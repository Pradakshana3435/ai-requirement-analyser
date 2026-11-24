# AI Requirement Analyser

A proof of concept that helps Business Analysts turn unstructured business requirements into
clear, structured and reviewable requirements. It classifies requirements, finds ambiguous,
incomplete, duplicate, conflicting and non-testable ones, and suggests improved requirements,
user stories, Given/When/Then acceptance criteria and clarification questions. Every item is linked
to the exact source text, flagged if it adds facts the source does not contain, and left for the
analyst to accept, edit or reject. Results export to Word, CSV and Markdown.

The tool only suggests. A Business Analyst makes every decision.

## Features

- Input: pasted text, or PDF, DOCX and TXT files (text-based PDFs only; scanned PDFs are not supported).
- Splits the text into individual requirements, each linked to its source quote.
- Classifies each into 7 types: functional, non functional, business rule, constraint, assumption,
  dependency, open question.
- Finds ambiguous, incomplete, duplicate, conflicting and non-testable requirements.
- Suggests improved requirements, user stories, acceptance criteria and clarification questions.
  Missing details become `[TBD: ...]` placeholders instead of invented values.
- Checks suggestions for numbers, terms and named systems that are not in the source and marks them
  "Unsupported".
- Review step: accept, edit or reject each item; edited text is kept next to the AI text.
- Report: summary, inventory, findings, suggestions, traceability and review status as Word (.docx),
  CSV and Markdown. Rejected items go to an appendix; unreviewed items are labelled as such.

## Requirements

- Python 3.11 or newer
- A Groq API key (free tier is enough for trials, but is rate limited)

## Setup (Windows)

```bat
cd req-analyser
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

In PowerShell, activate with `.venv\Scripts\Activate.ps1`. If scripts are blocked, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use the cmd activation above.

Create a file named `.env` in the project root (never commit it, never share it):

```text
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
MAX_UPLOAD_MB=10
MAX_PARALLEL=2
```

Optional settings:

| Setting | Purpose |
| --- | --- |
| `GROQ_MODEL_CLASSIFY`, `_SUMMARY`, `_NEWFACTS`, `_PAIRS`, `_SUGGEST` | Use a different (for example cheaper) model for one stage |
| `MAX_PARALLEL` | Number of model calls run at once. Raise it only if your key allows more requests per minute |
| `SUGGEST_SCOPE` | `flagged` (default) generates suggestions only for flagged requirements in large documents |
| `MAX_UPLOAD_MB` | Largest accepted upload |

Set `PYTHONUTF8=1` if the console shows encoding errors on Windows.

## Run the app

```bat
.venv\Scripts\activate.bat
streamlit run app.py
```

Open the address shown (usually http://localhost:8501) and follow the four steps: **1. Input**,
**2. Inventory**, **3. Review**, **4. Report**. See `docs/USER_GUIDE.md`. Results are kept only
while the browser tab is open, so download the report before closing it.

## Run from the command line

```bat
python run_pipeline.py data\samples\sample_01.txt
```

This prints a summary and saves `output\analysis.json`.

## Tests

```bat
python -m pytest -q
```

The tests do not call the model. Manual test cases are in `docs/TEST_CASES.md`.

## Evaluation

The project includes 22 synthetic documents with gold labels (`data/eval`) and 5 held-out documents
(`data/heldout`).

```bat
python tools\validate_gold.py                    (check the gold files)
python -m eval.run_eval                          (run all 22 documents; resumes if interrupted)
python -m eval.run_eval --data data/heldout      (run the held-out set)
python -m eval.run_eval --score-only             (rebuild the report from saved results)
```

Reports are written to `output/eval/report.md` and `output/heldout/report.md`. A sheet for rating
suggestion usefulness by hand is written to `review_sheet.csv` next to each report. Results and
limitations are described in `docs/EVALUATION_REPORT.md`.

## Project layout

```text
app.py                  Streamlit app (radio navigation: Input, Inventory, Review, Report)
pipeline.py             Runs all analysis stages
config.py, models.py    Settings and data models
ingest/                 Text extraction and requirement splitting
analysis/               Classification, quality, duplicates and conflicts, suggestions, summary
validate/               Source-quote grounding and the new-fact check
llm/                    Model client (retries, caching, rate-limit handling) and parallel helper
export/report.py        Word, CSV and Markdown report builders
ui/                     Input, Inventory, Review and Report tabs
eval/                   Scoring and evaluation runner
tools/                  Dataset builder and gold-file validator
data/                   Samples, evaluation set and held-out set
docs/                   User guide, test cases, evaluation report
tests/                  Automated tests
```

## Known limitations

- Scanned (image-only) PDFs are not supported; there is no OCR.
- Conflicts between requirements that share very little wording can be missed.
- Short requirements that lack a detail are caught less reliably than vague wording.
- The free API tier limits requests per minute and per day, so large documents can be slow.
- Session state is lost when the browser is refreshed.
- User-story benefits ("so that ...") are the model's inference and are not checked against the source.

## Security and data

- Keep `.env`, `.cache/` and `output/` out of version control. Never paste API keys into chat or commands.
- Document text is sent to the configured AI provider. Use synthetic or sanitised documents unless
  your organisation allows otherwise.
