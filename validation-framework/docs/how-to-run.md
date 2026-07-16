# How to Run

End-to-end instructions for running the validation harness against an OLS instance.

## What this does (in 5–10 lines)

For each prompt in the bank, the harness sends the prompt text to the OpenShift Lightspeed `/v1/query` API, captures the response and the documents OLS cited, and scores the result on four dimensions: **citation recall** (did OLS cite the expected `tvk-content/CRDs/*.md`?), **fact coverage** (rubric prompts only — does the prose answer contain every `expected_facts` entry, judged by a separate LLM?), **YAML hallucination** (yaml_baseline prompts only — every generated CR is checked field-by-field against the real TVK CRD schemas under `validator/crds/`; unknown fields are flagged as hallucinations), and **parameter match** (yaml_baseline prompts only — does each generated CR contain the `expected_parameters` from the prompt's `yaml_validation` entries?). It then writes a per-prompt summary table, a per-category breakdown, and a detailed report per prompt with citation diffs, fact verdicts, generated YAML, and field-by-field results — so you can see which prompts regressed when you change `tvk-content/`.

## Prerequisites

- Python 3.10+ with the validator venv set up: `cd validator && python3 -m venv venv && source venv/bin/activate && pip install pyyaml requests tabulate urllib3`.
- A running OLS instance with `/v1/query` reachable.
- A Bearer token for the OLS endpoint.
- A Groq API key (the harness uses a separate Groq model as the "judge" LLM for rubric fact-coverage scoring).
- The TVK CRD YAMLs already vendored in `validator/crds/` (used for the hallucination check; nothing to install).

## Environment variables

All required, exported in the shell before running. The validator reads them via `os.getenv` in [run.py:16-23](../validator/run.py#L16-L23).

| Variable | Purpose | Example |
|---|---|---|
| `OLS_URL` | Full URL to the OLS `/v1/query` endpoint. The harness POSTs prompts here. | `https://lightspeed.apps.<cluster>.example.com/v1/query` |
| `TOKEN` | Bearer token for OLS auth. Sent as `Authorization: Bearer $TOKEN`. | `sha256~...` |
| `OLS_MODEL` | Model name OLS should route the query to. | `meta-llama/llama-4-scout-17b-16e-instruct` |
| `OLS_PROVIDER` | LLM provider OLS should use. Optional — only needed when OLS is configured with multiple providers. | `groq-2` |
| `GROQ_KEY` | API key for the Groq endpoint used by the judge LLM (rubric fact scoring). | `gsk_...` |
| `GROQ_MODEL` | Groq model name to use as the judge. | `llama-3.3-70b-versatile` |

If any of `OLS_URL` / `TOKEN` / `OLS_MODEL` are missing, OLS calls will fail. If `GROQ_KEY` / `GROQ_MODEL` are missing, rubric prompts will fail at the fact-coverage step (yaml_baseline prompts still work — they don't call the judge).

## Running a single prompt

Useful while authoring or debugging a prompt.

```bash
cd validator
source venv/bin/activate
export OLS_URL=...
export TOKEN=...
export OLS_MODEL=...
export OLS_PROVIDER=...     # optional
export GROQ_KEY=...
export GROQ_MODEL=...

python run.py -p ../prompts/v1/target/007-s3-yaml.yaml
```

## Running the full bank

Point `-d` at a directory; the harness walks it recursively and processes every `.yaml` / `.yml` file.

```bash
# All v1 essential prompts
python run.py -d ../prompts/v1

# Or all v2 extended prompts
python run.py -d ../prompts/v2

# Or one category across both
python run.py -d ../prompts/v1/target
```

## What you'll see

The harness prints four sections to stdout, in order:

1. **Run summary** — total prompts, average overall score, pass/fail counts, best & worst scores, and the pass criteria (`overall ≥ 0.8` AND no hallucinations AND schema valid).
2. **Per-prompt summary table** — one row per prompt with the score breakdown: overall, citation recall, fact score (rubric only), parseable YAML count, hallucination flag, schema flag, params match (yaml_baseline only). Sorted worst-first so the regressions are at the top.
3. **Per-category summary** — average / min / max / pass / fail by category, plus the worst-scoring prompt in each. This is the table that drives the docs-todo list: a category averaging 0.4 means that CRD's `tvk-content/` doc is the weakest link.
4. **Detailed per-prompt breakdown** — for every prompt: the query, score, expected vs retrieved citations (with what was missed), the full LLM response, the per-fact `COVERED` / `MISSING` verdicts (rubric), and for yaml_baseline the matched / absent / extra CRs, the generated YAML, field-by-field expected-vs-actual diffs, hallucinated fields, and CRD-schema errors.

Pipe to a file when running the full bank — output is verbose:

```bash
python run.py -d ../prompts/v1 | tee run-$(date -u +%Y%m%dT%H%M%SZ).log
```

## Iterating on `tvk-content/`

The typical feedback loop:

1. Run the harness against the current `tvk-content/` (baseline). Note the per-category scores and the prompts in the FAIL list.
2. For the worst-scoring prompts, the detailed breakdown will tell you which dimension failed — missed citations (the relevant CRD doc isn't being retrieved), missing facts (the doc is retrieved but doesn't say what it should), or wrong field names / hallucinations (the doc has incorrect API details).
3. Edit `tvk-content/`, rebuild the RAG image, redeploy OLS.
4. Re-run the harness. Compare the new summary table against the baseline — score deltas per category tell you whether the doc edit helped.

## Common gotchas

- **OLS replies with `"response": null`** — usually means OLS couldn't reach its provider or the token expired. Re-export `TOKEN`, re-test with a single prompt.
- **All citation recalls are 0.0** — OLS is returning a response but no `referenced_documents`. Check the OLS config; without retrievals, the harness can't score citation accuracy.
- **Rubric prompts hang or error at fact-coverage** — Groq judge LLM is rate-limited or `GROQ_KEY` is wrong. Try a smaller subset first.
- **A yaml_baseline prompt scores 0** — either OLS produced no YAML at all, or every CR it produced failed the basic structure check (`apiVersion` / `kind` / `metadata.name` missing). The detailed breakdown's "LLM RESPONSE" section will show what OLS actually returned.
