import json
import yaml
from tabulate import tabulate
import logging
logger = logging.getLogger("harness.report")


def is_passing(r):
    """A prompt passes if score >= 0.8, no hallucinations, and schema is valid"""
    b = r.get("breakdown", {})
    hallucination = b.get("hallucination")
    schema_valid = b.get("schema_valid")

    score_ok = r["overall"] >= 0.8
    no_hallucinations = hallucination is None or hallucination == 1
    schema_ok = schema_valid is None or schema_valid == 1

    return score_ok and no_hallucinations and schema_ok


def print_summary_table(results):
    """Print a tabulate table with per-prompt scores"""

    headers = [
        "#", "Prompt ID", "Mode", "Result", "Overall",
        "Citation", "Facts", "Parseable",
        "Hallucination", "Schema", "Params"
    ]

    rows = []
    for i, r in enumerate(results, 1):
        b = r.get("breakdown", {})
        mode = r.get("validation_mode", "?")
        result = "PASS" if is_passing(r) else "FAIL"

        rows.append([
            i,
            r.get("id", "?"),
            mode,
            result,
            _fmt_score(r.get("overall")),
            _fmt_score(b.get("citation_recall")),
            _fmt_score(b.get("fact_score")) if mode == "rubric" else "NA",
            _fmt_score(b.get("yaml_parseable")),
            _fmt_score(b.get("hallucination")),
            _fmt_score(b.get("schema_valid")),
            _fmt_score(b.get("params")) if mode == "yaml_baseline" else "NA",
        ])

    rows.sort(key=lambda r: float(r[4]) if r[4] != "NA" else 999)

    print("\n" + tabulate(rows, headers=headers, tablefmt="rounded_grid",
                          numalign="center", stralign="center"))


def print_category_summary(results):
    """Print per-category averages"""

    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    headers = ["Category", "Count", "Avg Score", "Min", "Max", "Pass", "Fail", "Worst Prompt"]
    rows = []

    for cat in sorted(categories):
        cat_results = categories[cat]
        scores = [r["overall"] for r in cat_results]
        worst = min(cat_results, key=lambda r: r["overall"])
        passing = sum(1 for r in cat_results if is_passing(r))
        rows.append([
            cat,
            len(cat_results),
            f"{sum(scores)/len(scores):.2f}",
            f"{min(scores):.2f}",
            f"{max(scores):.2f}",
            passing,
            len(cat_results) - passing,
            f"{worst.get('id', '?')} ({worst['overall']:.2f})"
        ])

    rows.sort(key=lambda r: float(r[2]))

    print("\n" + tabulate(rows, headers=headers, tablefmt="rounded_grid",
                          numalign="center", stralign="center"))


def print_detailed_breakdown(results):
    """Print detailed per-prompt breakdown with full context"""

    total = len(results)

    print(f"\n{'=' * 70}")
    print(f"DETAILED BREAKDOWN")
    print(f"{'=' * 70}")

    for i, r in enumerate(results, 1):
        print(f"\n{'=' * 70}")
        print(f"[{i}/{total}] {r.get('id', '?')} — {r.get('query', '?')}")
        print(f"{'=' * 70}")

        # Score with pass/fail
        result_str = "PASS ✓" if is_passing(r) else "FAIL ✗"
        print(f"\nScore: {r['overall']:.2f} — {result_str}")
        parts = []
        for k, v in r.get("breakdown", {}).items():
            parts.append(f"{k}={_fmt_score(v)}")
        if parts:
            print(" | ".join(parts))

        detail = r.get("detail", {})
        citation = detail.get("citation", {})

        # Citations
        print(f"\n{'─' * 40}")
        print(f"CITATIONS")
        print(f"{'─' * 40}")

        print(f"\nExpected:")
        for c in citation.get("expected", []):
            print(f"  - {c}")

        print(f"\nRetrieved:")
        for c in citation.get("retrieved", []):
            print(f"  - {c}")

        missed = citation.get("missed", [])
        if missed:
            print(f"\nMissed:")
            for c in missed:
                print(f"  - {c}")
        else:
            print(f"\nMissed: None")

        # LLM Response
        print(f"\n{'─' * 40}")
        print(f"LLM RESPONSE")
        print(f"{'─' * 40}")

        llm_response = detail.get("llm_response", "")
        if llm_response:
            print()
            for line in llm_response.split("\n"):
                print(line)

        # Facts
        fact_details = detail.get("facts", {})
        if fact_details:
            print(f"\n{'─' * 40}")
            print(f"FACT COVERAGE")
            print(f"{'─' * 40}")
            print()
            for fact, verdict in fact_details.items():
                marker = "✓" if verdict == "COVERED" else "✗"
                print(f"{marker} [{verdict}] {fact}")

        # YAML CR Results
        yaml_detail = detail.get("yaml", {})
        category_results = yaml_detail.get("category_results", [])

        if category_results:
            print(f"\n{'─' * 40}")
            print(f"YAML VALIDATION RESULTS")
            print(f"{'─' * 40}")

            for cr in category_results:
                status = cr.get("status")

                if status == "matched":
                    ek = cr.get("expected_kind")
                    ev = cr.get("expected_api_version")
                    passed = cr.get("passed")
                    fields_covered = cr.get("fields_covered", "?")
                    marker = "✓" if passed else "✗"
                    print(f"\n{marker} {ek} ({ev}) — {fields_covered} fields matched")

                    # Show generated YAML
                    llm_yaml = cr.get("llm_response", {})
                    if llm_yaml:
                        print(f"\n  Generated YAML:")
                        for line in yaml.safe_dump(llm_yaml, default_flow_style=False).split("\n"):
                            if line.strip():
                                print(f"    {line}")

                    # Show field-by-field results
                    field_results = cr.get("field_results", {})
                    if field_results:
                        print(f"\n  Expected Parameters:")
                        for field, result in field_results.items():
                            if result == "ok" or "present" in str(result):
                                print(f"    ✓ {field}: {result}")
                            else:
                                print(f"    ✗ {field}: {result}")

                elif status == "absent":
                    ek = cr.get("expected_kind")
                    ev = cr.get("expected_api_version")
                    print(f"\n✗ {ek} ({ev}) — NOT GENERATED")
                    print(f"  Reason: {cr.get('reason', '?')}")

                elif status == "extra":
                    ak = cr.get("actual_kind")
                    av = cr.get("actual_api_version")
                    print(f"\n⚠ {ak} ({av}) — EXTRA (not in expected list)")

        # Hallucination check
        hallucinated = yaml_detail.get("hallucinated_fields", [])
        print(f"\n{'─' * 40}")
        print(f"HALLUCINATION CHECK")
        print(f"{'─' * 40}")
        if hallucinated:
            print(f"\nHallucinated Fields ({len(hallucinated)}):")
            for f in hallucinated:
                print(f"  ✗ {f}")
        else:
            print(f"\nHallucinated Fields: None")

        # Schema validation
        schema_errors = yaml_detail.get("schema_errors", [])
        print(f"\n{'─' * 40}")
        print(f"SCHEMA VALIDATION")
        print(f"{'─' * 40}")
        if schema_errors:
            print(f"\nErrors ({len(schema_errors)}):")
            for e in schema_errors:
                print(f"  ✗ {e}")
        else:
            print(f"\nStatus: Passed")


def print_overall_stats(results):
    """Print high-level run statistics"""

    total = len(results)
    if total == 0:
        print("No results to summarize.")
        return

    scores = [r["overall"] for r in results]
    avg = sum(scores) / total
    passing = sum(1 for r in results if is_passing(r))

    print(f"\n{'=' * 70}")
    print(f"  VALIDATION RUN SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Prompts: {total}")
    print(f"  Average Score: {avg:.2f}")
    print(f"  Pass: {passing}  |  Fail: {total - passing}")
    print(f"  Pass criteria: score >= 0.8, no hallucinations, valid schema")
    print(f"  Best:  {max(scores):.2f}  |  Worst: {min(scores):.2f}")


def print_full_report(results, threshold=0.6):
    """Print the complete report"""
    print_overall_stats(results)
    print_summary_table(results)
    print_category_summary(results)
    print_detailed_breakdown(results)


def save_jsonl(results, filepath):
    """Write results as JSONL"""
    with open(filepath, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    logger.info(f"Results written to {filepath}")


def _fmt_score(value):
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"