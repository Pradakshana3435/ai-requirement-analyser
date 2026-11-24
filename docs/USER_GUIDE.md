# AI Requirement Analyser: User Guide

For Business Analysts. The tool turns unstructured requirement text into structured,
reviewable requirements. It suggests; **you decide**.

## 1. Start the app

1. Open Command Prompt and go to the project folder.
2. Run `.venv\Scripts\activate.bat`, then `streamlit run app.py`.
3. Open the Local URL shown (for example http://localhost:8501).

## 2. The four steps

Use the step selector at the top of the page. Your work is kept while the app is open.
Refreshing the browser clears it, so download your report before you close the tab.

### Step 1: Input
- Paste text, or upload a PDF, DOCX or TXT file (maximum size is shown on the page).
- Press **Analyse**. The progress bar shows each stage. Large documents take longer.
- Scanned PDFs (images of text) are not supported. Use a text PDF or paste the text.
- Warnings appear after analysis. A warning such as "not checked by the model" means that
  one stage could not finish; the rest of the results are still valid.

### Step 2: Inventory
- Every requirement found, with its type and the exact source text.
- Types: functional, non functional, business rule, constraint, assumption,
  dependency, open question.
- If a requirement was split or typed wrongly, note it for your review; edits to the
  requirement text are made in your source document.

### Step 3: Review
Findings (problems the tool found) and Suggestions (improved requirements, user stories,
acceptance criteria, clarification questions) are listed 10 per page.

| Action | Meaning |
| --- | --- |
| Accept | You agree with the item. |
| Edit | You change the wording; your version is what appears in the report. |
| Reject | You disagree. The item moves to the report appendix. |
| Pending | Not reviewed yet. The report says so. |

**Unsupported flag.** A suggestion marked unsupported introduces a number, name or
term that is not in your source text. Do not accept it unless you confirm the fact. A
`[TBD: ...]` marker means the tool is asking you for missing information instead of
guessing.

**Severity** (low, medium, high) shows how serious a finding is. Start with high.

### Step 4: Report
- Shows how many items are accepted, edited, rejected and not yet reviewed.
- Download **Word (.docx)** for sharing, **Excel/CSV** for tracking (one row per
  requirement), or **Markdown** for wikis.
- Sections: Summary, Inventory, Quality Findings, Improved Requirements, User Stories,
  Acceptance Criteria, Clarification Questions, Traceability, Review Status, and an
  appendix of rejected items.

## 3. What the findings mean

- **Ambiguous**: vague words such as "fast", "user friendly", "as needed".
- **Incomplete**: key information is missing (who, how much, when, what happens on failure).
- **Duplicate**: two requirements say the same thing.
- **Conflict**: two requirements cannot both be true (for example 2 days vs 5 days).
- **Non testable**: no measurable pass or fail condition exists.

## 4. Good practice

- The tool can miss issues, especially conflicts between requirements that share few
  words. Treat it as a second reader, not a replacement for your judgement.
- Check every suggestion against the source quote shown next to it.
- Do not upload confidential documents unless your organisation allows sending the text
  to the AI provider. Use sanitised text for trials.
- Keep your API key in the `.env` file only. Never share it.

## 5. Troubleshooting

| Problem | What to do |
| --- | --- |
| "Rate limit" waits or slow analysis | The AI provider limits requests. Wait, or use a key with higher limits. |
| Analysis failed with an API error | Check `.env` for a valid key and model name. |
| A requirement is missing | Check the quote in the source; report it as a splitting error. |
| Report buttons do nothing | Run an analysis first on the Input step. |
