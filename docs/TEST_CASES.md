# Test Cases

Automated tests run with `python -m pytest -q`. Manual tests follow.

## Automated coverage

| Area | Test file | What it checks |
| --- | --- | --- |
| Data models | test_models.py | Enums, spans, final text of edited suggestions |
| Extraction | test_extract.py | TXT, DOCX, PDF, empty and oversized files, pasted text |
| LLM client | test_llm_client.py | JSON parsing, retries, caching, failure handling |
| Splitting | test_split.py | Quotes mapped to real offsets, tolerant matching |
| Classification | test_classify.py | Type assignment, invalid labels |
| Quality | test_quality.py | Ambiguity, incompleteness, non testable findings |
| Duplicates and conflicts | test_pairs.py | Shortlisting, judging, evidence |
| Suggestions | test_suggest.py | Four suggestion kinds, scope limits |
| New facts | test_new_facts.py | Numbers and terms not in the source are flagged |
| Pipeline | test_pipeline.py | Stage order, progress, failure becomes a warning |
| UI | test_ui.py | Input, Inventory, Review paging, Report tabs |
| Export | test_report.py | Section order, status labels, DOCX, CSV, Markdown |
| Evaluation | test_eval.py | Metrics and gold dataset consistency |

## Manual test cases

| ID | Scenario | Steps | Expected result |
| --- | --- | --- | --- |
| M-01 | Paste text | Paste sample_01 text, Analyse | 13 requirements, findings for the vague, duplicate and conflicting lines |pass
| M-02 | Upload PDF | Upload data/samples/spec.pdf | Requirements listed, each with a source quote |pass
| M-03 | Upload DOCX | Upload a Word file | Same as M-02 |pass
| M-04 | Unsupported file | Upload a .png | Clear error message, app keeps working |pass
| M-05 | Empty input | Press Analyse with no text | Message asking for input |pass
| M-06 | Oversized file | Upload a file above the limit | Rejected with the size limit shown |pass
| M-07 | Accept item | Accept a suggestion | Status shows Accepted; report counts update |pass
| M-08 | Edit item | Edit a suggestion text | Report shows the edited text and status Edited |pass
| M-09 | Reject item | Reject a finding | Missing from main report sections; present in appendix |pass
| M-10 | Unsupported fact | Find a suggestion with an added number | Flagged Unsupported with the added term |pass
| M-11 | Traceability | Pick a requirement | Source quote, findings and suggestions are linked |pass
| M-12 | Export | Download DOCX, CSV, Markdown | Files open; CSV has one row per requirement |pass
| M-13 | Provider failure | Use an invalid key | Readable error, no crash |pass
| M-14 | Rate limit | Run a large PDF on a low limit key | Waits and retries, or reports a warning |pass
| M-15 | Start over | Press Start over | Inputs and results cleared |pass
