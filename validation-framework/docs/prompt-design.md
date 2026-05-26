# Prompt Design

How validation prompts are written, what each field means, and how to add a new one.

## Where prompts live

```
validation-framework/prompts/
├── v1/   # essential set — every TVK CRD has at least one prompt (39 files)
└── v2/   # extended set — edge cases, variants, advanced features (74 files)
```

Within each version, prompts are grouped by category (one subdirectory per CRD or scenario family):

```
prompts/v1/
├── target/        backupplan/    backup/       restore/
├── snapshot/      hook/          policy/       license/
├── clusterbackup/ clusterbackupplan/  clusterrestore/
├── continuousrestoreplan/      triliovaultmanager/
├── scheduling/    application/   composite/    advanced/
└── restore-scenarios/
```

File names follow `00X-short-slug.yaml` — the leading number is just for ordering inside a category, nothing depends on it.

## Why prompts are grounded in the gitbook, not in `tvk-content/`

`tvk-content/` is the markdown corpus shipped to OpenShift Lightspeed (OLS) as its RAG knowledge base. The whole point of the validation framework is to **measure and improve** that corpus, so it cannot also be the source of truth for "is this answer correct."

Every prompt's `expected_facts` and `yaml_validation` are grounded in the canonical Trilio docs (docs.trilio.io / GitBook). The `expected_citations` then point at the `tvk-content/CRDs/*.md` file we expect OLS to retrieve — that's how the framework asks "does OLS pull the right doc, and does that doc tell the truth?"

A discrepancy between gitbook truth and what `tvk-content/` causes OLS to answer is exactly the signal the framework is designed to surface.

## The two validation modes

Each prompt declares one of two modes via `validation_mode`. The mode determines which fields the prompt has and how the harness scores it.

### `rubric` — conceptual questions

For "how does X work?" / "what fields does Y need?" / "what are the valid values for Z?" — anything where the answer is prose, not YAML.

```yaml
id: target-s3-required-fields
category: target
validation_mode: rubric
prompt: "What fields are required to configure an S3 Target?"
expected_facts:
  - "spec.type must be ObjectStore"
  - "spec.vendor should be AWS for AWS S3"
  - "spec.objectStoreCredentials.region is required"
  - "spec.objectStoreCredentials.bucketName is required"
  - "spec.objectStoreCredentials.credentialSecret references a Secret containing accessKey and secretKey"
expected_citations:
  - "tvk-content/CRDs/target-crd.md"
tags:
  - cr-api
  - required-fields
  - s3
```

How it's scored: a judge LLM reads OLS's prose answer and marks each `expected_facts` entry `COVERED` or `MISSING`. The score is `covered / total`.

**Writing tips**
- Each fact should be a single atomic claim — easier for the judge to mark cleanly.
- Use exact field paths (`spec.objectStoreCredentials.region`) — vague facts like "S3 needs credentials" pass too easily.
- 4–7 facts per prompt is the sweet spot. Too few = trivially passable; too many = signal lost in noise.

### `yaml_baseline` — YAML generation

For "show me YAML to create…" / "give me an example of…" — anything where the LLM is expected to emit one or more Kubernetes CRs.

```yaml
id: target-s3-yaml
category: target
validation_mode: yaml_baseline
prompt: "Show me YAML to create an S3 Target named 'backup-target' with bucket 'my-backups' in region us-east-1."
expected_citations:
  - "tvk-content/CRDs/target-crd.md"
yaml_validation:
  - expected_kind: "Target"
    expected_api_version: "triliovault.trilio.io/v1"
    expected_parameters:
      metadata.name: "backup-target"
      spec.type: "ObjectStore"
      spec.vendor: "AWS"
      spec.objectStoreCredentials.bucketName: "my-backups"
      spec.objectStoreCredentials.region: "us-east-1"
      spec.objectStoreCredentials.credentialSecret.name: "*"
  - expected_kind: "Secret"
    expected_api_version: "v1"
    expected_parameters:
      type: "Opaque"
      stringData.accessKey: "*"
      stringData.secretKey: "*"
tags:
  - cr-creation
  - yaml-generation
  - s3
```

How it's scored: each YAML block in the response is parsed, run through the CRD schema (hallucinated-fields check), then matched against `yaml_validation` entries by `expected_kind`. Per-entry field score is `matched_fields / expected_fields`; the prompt's params score is the aggregate across all entries.

**`yaml_validation` is a list.** One entry per CR the LLM should return. Most Target prompts need 2 entries (Secret + Target). Composite workflows can need 3+ (Secret + Target + BackupPlan, etc.). The harness matches by `expected_kind`; if multiple LLM YAMLs share a Kind, the best field-match wins.

**Per-entry fields:**
- `expected_kind` (required) — must equal the LLM YAML's `kind`.
- `expected_api_version` (required) — must equal the LLM YAML's `apiVersion`.
- `expected_parameters` (required) — dot-path → expected value.
  - Concrete values: `spec.type: "ObjectStore"` requires that exact value.
  - Wildcard `"*"`: field must be present, any value (use this when the prompt doesn't specify a value — e.g., the credentialSecret name, the namespace, etc.).

**Writing tips**
- Pin every value the prompt explicitly mentions (`my-backups`, `us-east-1`). Anything else gets `"*"`.
- Include the `kind` for every CR the LLM should return — including Secrets / ConfigMaps. Missing a Kind means the harness can't notice when OLS skips it.
- Don't list fields the prompt didn't ask for. The hallucination check (separate) will already flag fields that aren't in the CRD schema; listing every legitimate field here turns the score into a noise floor.

## Common fields (both modes)

| Field | Meaning |
|---|---|
| `id` | Unique slug. Used as the row key in reports. |
| `category` | Top-level grouping for per-category scoring (`target`, `backupplan`, `composite`, …). Should match the parent directory name. |
| `prompt` | The exact text sent to OLS. |
| `expected_citations` | List of `tvk-content/CRDs/*.md` paths we expect OLS to cite. Used for citation recall. |
| `tags` | Free-form labels for filtering (`cr-api`, `s3`, `yaml-generation`, `edge-case`, …). Not used by the scorer; useful for slicing reports. |

## Adding a new prompt

1. **Pick the right directory.** A prompt about Backup CR fields → `v1/backup/` if it's foundational, `v2/backup/` if it's an edge case or variant. v1 is "must work"; v2 is "should work."
2. **Pick a slug.** `<next-number>-<short-description>.yaml`. The number is just for sort order — pick the next free integer in the category.
3. **Pick a mode.** Conceptual question → `rubric`. Asks for YAML → `yaml_baseline`. Don't mix; if a question is "explain X and show me YAML for it", split it into two prompts.
4. **Ground every claim in the gitbook.** Open <https://docs.trilio.io/kubernetes/5.2.x/getting-started/using-trilio/getting-started-1/triliovault-crds> (canonical YAML examples) and <https://docs.trilio.io/kubernetes/reference/custom-resource-definition-application> (field reference). Every `expected_fact` and every `expected_parameters` key should be traceable to one of those pages.
5. **Set `expected_citations`** to the relevant `tvk-content/CRDs/*.md` file(s). Composite prompts cite multiple CRDs.
6. **Run it once** locally with `validator/run.py -p <your-new-file>` and confirm the structure is accepted and the OLS response gets scored. Iterate on the prompt wording if the model is consistently misunderstanding the question.

## What NOT to do

- Don't reference the local `tvk-content/` to figure out what the right answer is. If the gitbook doesn't say it, don't assert it.
- Don't add an `invalid_parameters` field. It was removed from the schema. If you need to assert "field X must not appear" for a specific edge case, raise it and we'll re-introduce the field selectively.
- Don't change the `validation_mode` of an existing prompt unless you understand the downstream impact — the harness behavior, the report format, and historical baselines all key off mode.
- Don't add a `priority` field. Deprecated.
