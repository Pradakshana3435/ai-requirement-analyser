# Evaluation Report: AI Requirement Analyser (PoC)

Status: draft. Items marked **[TO FILL]** need a manual step (see section 8).

## 1. Purpose

Measure how well the analyser turns unstructured requirement text into structured,
reviewable output, and where it still fails.

## 2. Method

- **Dataset:** 22 synthetic requirement documents from 22 business domains (library, banking,
  ticketing, payroll and others), 8 to 9 requirements each, in three layouts (numbered lines,
  bullets, prose). Files: `data/eval/docs`.
- **Gold labels:** `data/eval/gold`. For every document: the correct requirements (181 in total),
  their type (7 types), and 89 planted issues: 30 ambiguous, 22 incomplete, 20 non-testable,
  12 conflicts, 5 duplicates. Labels were written by the project author.
- **Held-out set:** 5 further documents (60 requirements, 25 planted issues) in `data/heldout`,
  written after the prompts were tuned and never used for tuning. They are messier than the main
  set: an email, meeting notes, flowing paragraphs, sentences containing two requirements, and
  informal bullets. They were written by the AI assistant that helped build the tool, not by an
  independent human, which limits how independent the test is.
- **Run:** `python -m eval.run_eval` runs the full pipeline on each document and scores it
  against the gold labels. Matching of requirements uses overlap of source offsets, with a
  text-similarity fallback. A planted issue counts as found when the analyser reports the same
  kind on the same requirement (both requirements for duplicates and conflicts).
- **Model:** Groq free tier, `openai/gpt-oss-120b` (main) and `openai/gpt-oss-20b` (per-stage
  override for several stages).

## 3. Results

| Measure | Result |
| --- | --- |
| Requirement splitting (precision / recall / F1) | 100% / 100% / 100% |
| Type accuracy (7 types) | 93.4% |
| Issue detection overall (precision / recall / F1) | 64.8% / 88.8% / 74.9% |
| Requirements with a valid source span | 100% |
| Findings grounded in the source text | 100% |
| Suggestions flagged as unsupported by the new-fact check | 16.3% (see note) |

Per issue kind:

| Issue | Gold | Predicted | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| ambiguous | 30 | 41 | 68.3% | 93.3% | 78.9% |
| incomplete | 22 | 32 | 50.0% | 72.7% | 59.3% |
| duplicate | 5 | 3 | 100.0% | 60.0% | 75.0% |
| conflict | 12 | 13 | 92.3% | 100.0% | 96.0% |
| non-testable | 20 | 33 | 60.6% | 100.0% | 75.5% |

Type confusions (gold, then predicted): 5 constraints were called business rules, 3 functional
requirements were called business rules, 2 business rules were called functional. All 9
assumptions, 7 open questions and 30 non-functional requirements were typed correctly.

**Notes on the numbers**

- **Precision is understated.** A finding counts as correct only if it matches a planted issue.
  Many unmatched findings are genuine gaps that were not planted, for example "encryption
  algorithm not specified". The author judged all 43 unmatched findings: 29 (67%) were valid, which gives an **adjusted
  precision of about 88.5%** (raw 64.8%). These judgements were made by the author, so they are
  subjective and not independent; a Business Analyst's rating would be stronger.
- **Unsupported rate.** Includes suggestions the new-fact check could not run on (after rate-limit
  failures), which are conservatively left as unsupported. Pipeline warnings: 5.
- **Speed.** Average 25.3 s per document on the free tier. This is not a cold-cache benchmark:
  some stages were served from cache, and many calls waited on rate limits. A clean timing needs
  a higher-limit key.

## 3b. Held-out results (5 unseen documents)

| Measure | 22 tuned documents | 5 held-out documents |
| --- | --- | --- |
| Requirement splitting, precision / recall | 100% / 100% | 100% / 98.3% |
| Type accuracy | 93.4% | 89.8% |
| Issue recall, overall | 88.8% | 96.0% |
| Issue precision, overall | 64.8% | 58.5% |
| Incomplete precision | 50.0% | 26.7% |
| Conflict precision / recall | 92.3% / 100% | 83.3% / 100% |
| Duplicate recall | 60.0% | 100% |
| Findings and spans grounded in the text | 100% | 100% |
| Suggestions flagged unsupported | 16.3% | 14.6% |
| Pipeline warnings | 5 | 0 |
| Average seconds per document (free tier, uncached) | 25.3 (partly cached) | 76.5 |

How to read this:

- **No sign of overfitting to the tuned set.** Splitting, grounding, conflict detection and the
  unsupported rate are about the same on unseen text. Type accuracy fell 3.6 points, which is
  within what five documents can produce.
- **Recall is high but the sample is small.** 24 of 25 planted issues were found; with 25 issues
  the true rate could plausibly lie anywhere from about 80% to 99%.
- **The one splitting miss** was a sentence that held two requirements ("fill the application form
  online and save it as a draft before submitting"), which the tool kept as one requirement.
- **"Incomplete" is the main precision problem.** The tool reported 15 incomplete findings against
  5 planted; many are plausible but over-reported, especially on dependency statements.
- **Speed.** All calls on this run were uncached, but the free tier limits requests, so 7 to 104 s
  per document mostly reflects rate-limit waits.

## 4. Changes made during evaluation and their effect

| Change | Reason | Effect |
| --- | --- | --- |
| New-fact check ignores story and Given/When/Then wording | Normal phrasing such as "As a patient" was flagged as invented | Unsupported flags fell from 67% (first 3 documents) to about 16% |
| Stemmed pair shortlist, 4 neighbours, clearer conflict definition | "Cash only" versus "card or wallet" never reached the model | Conflict recall 100% (was missing this case) |
| Quality prompt separates vague wording from missing detail, allows several findings per requirement | Wrong kind assigned; vague quality statements flagged once | Issue recall 88.8% across 22 documents |
| Classification prompt with sharper definitions | Business rules called functional, constraints mostly wrong | Type accuracy 81.8% to 90.6% |
| Classification reads the original quote | Rewritten text had lost the "Assumption:" prefix | Type accuracy 93.4%; assumptions 4/9 to 9/9 |
| Schema accepts acceptance criteria returned as objects | One batch of suggestions failed in one document | Pipeline warnings 8 down |

## 5. Good examples

- Conflict found: "A member may borrow up to 5 books at a time" versus "up to 8 books at a time".
- Conflict found after the shortlist fix: payment "in cash only" versus payment "by card or wallet".
- Missing information handled without invention: "Passengers can check in online from 24 hours
  before departure until [TBD: end time]" and "Parents receive a message via [TBD: delivery
  method]".
- Useful clarification questions: "How long is the one-time code valid after generation?", "Who are
  considered the relevant people?".

## 6. Weak examples and limitations

- **Missed "incomplete" requirements on short statements** (72.7% recall): "Delivery partners are
  assigned based on proximity" (how?), "Extra baggage is charged at the standard rate" (which
  rate?), "Confirmation emails must be sent" (when, to whom?). The tool is better at spotting
  vague words than at spotting what is absent.
- **User-story benefits can be invented.** Phrases such as "so that I can securely access my
  account" are the model's inference. The new-fact check is deliberately lenient for the story
  format, so these are not flagged. The analyst review step is the safeguard.
- **Two of five planted duplicates were borderline** (the second statement adds detail). The tool's
  judgement is consistent with its own definition. The gold labels were not changed after the
  results were seen.
- **Minor false positive in the new-fact check:** "during transmission" flagged against the source
  "in transit".
- **Type boundary cases:** constraint versus business rule is subjective; a second labeller would
  likely disagree on some of the 5 cases.
- **Dataset realism.** The tuned documents are short and tidy, and the prompts were tuned on
  them, so those figures are optimistic. The held-out set (section 3b) is messier but small, and
  was written by the AI assistant, not by an independent person. Real emails, meeting notes and
  long specifications remain untested.
- **Other:** scanned PDFs are unsupported; session state is lost on browser refresh; conflicts
  between requirements with almost no shared wording can still be missed.

## 7. Conclusions

The pipeline splits requirements reliably, keeps every item linked to its source text, finds
most planted problems (88.8% recall) and avoids most invented facts. Its main weaknesses are
detecting what is missing from a short requirement and over-reporting issues (which the analyst
must review). Results on five unseen documents were consistent with those on the tuned set. It is suitable as an assistant that proposes findings for human review, which is
how the application is designed to be used.

## 8. To complete before submission

1. **Adjusted precision.** Done by the author: 29 of 43 unmatched findings valid, adjusted
   precision 88.5%. Optional: a second person rates the same rows to check agreement.
2. **BA usefulness.** A Business Analyst rates the rows of `output/eval/review_sheet.csv`
   (usefulness 1 to 5, accurate yes or no). Average usefulness: **[TO FILL]**; share accurate:
   **[TO FILL]**; raters: **[TO FILL]**.
3. **Held-out test.** Done for 5 documents (section 3b). Optional: add documents written by an
   independent person, ideally from real (sanitised) material.
4. **Second labeller** for the gold labels, ideally a Business Analyst: **[TO FILL]**.
5. **Cold-cache timing** on the higher-limit key: **[TO FILL]**.
