import os, yaml, argparse
from prompts import Prompt
from llm import LLM, llmtype
import constants
import re, subprocess, json
import helpers
from logger import logger


class ValidatePrompt:

    def __init__(self, prompt: Prompt, response: str, llm: LLM):
        self.prompt = prompt
        self.ols_response = response['response' ] if 'response' in response else None
        if 'referenced_documents' in response:
            self.ols_citations = [doc['doc_url'].removeprefix("/workdir/") for doc in response['referenced_documents']]
        else:
            self.ols_citations = None
        self.llm = llm
        self.citation_prompt_template = constants.citation_prompt_template

    def validate(self):
        logger.info(f"{'─' * 60}")
        logger.info(f"[{self.prompt.id}] ({self.prompt.validation_mode})")
        logger.info(f"  Query: {self.prompt.prompt[:80]}...")
        
        if self.ols_response is None or self.ols_citations is None:
            logger.error(f"  No OLS response")
            return {"id": self.prompt.id, "overall": 0, "error": "No OLS response"}

        results = {}
        results["citation"] = self.citation_validation()
        
        if self.prompt.validation_mode == "rubric":
            results["facts"] = self.fact_validation()
        else:
            results["facts"] = {"covered": 0, "total": 0, "missing": [], "details": {}}
        
        results["yaml"] = self.yaml_validation()
        
        score = self.score(results)
        score["id"] = self.prompt.id
        score["category"] = self.prompt.category
        score["validation_mode"] = self.prompt.validation_mode
        
        # Compact summary line
        parts = [f"Score: {score['overall']:.2f}"]
        for k, v in score["breakdown"].items():
            parts.append(f"{k}={v}")
        logger.info(f"  {' | '.join(parts)}")
        
        if score["actionable"]:
            for key, items in score["actionable"].items():
                if isinstance(items, list) and len(items) <= 3:
                    logger.info(f"  ⚠ {key}: {items}")
                elif isinstance(items, list):
                    logger.info(f"  ⚠ {key}: [{items[0]}, ... +{len(items)-1} more]")
                else:
                    logger.info(f"  ⚠ {key}: {items}")
        
        
        # In validate(), before returning score
        score["query"] = self.prompt.prompt
        score["detail"] = {
            "citation": {
                "expected": list(self.prompt.expected_citations),
                "retrieved": self.ols_citations,
                "missed": results["citation"]["missed"]
            },
            "llm_response": self.ols_response,
            "facts": results["facts"].get("details", {}),
            "yaml": {
                "expected_params": {},  # populated from category_results field_results
                "hallucinated_fields": results["yaml"]["hallucinated_fields"],
                "schema_errors": results["yaml"].get("schema_errors", []),
                "category_results": results["yaml"].get("category_results", [])
            }
        }

        # Extract expected_params from category results
        if results["yaml"]["category_results"]:
            for cr in results["yaml"]["category_results"]:
                if cr["status"] == "matched":
                    score["detail"]["yaml"]["expected_params"].update(cr.get("field_results", {}))
        return score

    def citation_validation(self):
        expected_citations = set(self.prompt.expected_citations)
        ols_citations = set(self.ols_citations)

        matched = expected_citations & ols_citations
        missed = expected_citations - ols_citations

        recall = len(matched) / len(expected_citations) if expected_citations else 0
        logger.info(f"[Citation Recall]: {recall:.2f} (matched: {len(matched)}, expected: {len(expected_citations)}, total: {len(ols_citations)})")

        return {
            "recall": recall,
            "matched": list(matched),
            "missed": list(missed),
            "total_expected": len(expected_citations),
            "total_retrieved": len(ols_citations)
        }

    def fact_validation(self):
        expected_facts = self.prompt.expected_facts
        ols_answer = self.ols_response
        rubric_prompt = constants.rubric_prompt_template.format(
            prompt=self.prompt.prompt,
            expected_facts=expected_facts,
            ols_answer=ols_answer
        )
        ols_response = self.llm.query(rubric_prompt)
        fact_coverage = json.loads(ols_response["choices"][0]["message"]["content"])

        covered = [k for k, v in fact_coverage.items() if v == "COVERED"]
        missing = [k for k, v in fact_coverage.items() if v == "MISSING"]

        logger.info(f"[Facts]: {len(covered)} / {len(expected_facts)} covered")
        # logger.info(f"[Fact Coverage]:\n {json.dumps(fact_coverage, indent=2)}")

        return {
            "covered": len(covered),
            "total": len(expected_facts),
            "missing": missing,
            "details": fact_coverage
        }

    def yaml_validation(self):
        yaml_blocks = self.yaml_extractor()
        logger.info(f"Yaml blocks from OLS Response: {len(yaml_blocks)} extracted")

        result = {
            "blocks_found": len(yaml_blocks),
            "parseable_count": 0,
            "full_yaml_count": 0,
            "hallucinated_fields": [],
            "schema_errors": [],          # was kubeconform_errors
            "category_results": None,
            "params_matched": 0,
            "params_total": 0,
            "missing_params": []
        }

        if not yaml_blocks:
            if self.prompt.validation_mode == "yaml_baseline":
                logger.error("No YAML blocks found in OLS response for yaml baseline validation")
            return result

        parsed = []
        for block in yaml_blocks:
            try:
                spec = yaml.safe_load(block)
                result["parseable_count"] += 1
            except yaml.YAMLError:
                logger.error(f"[Error parsing YAML]: {block}")
                continue
            if not self.is_full_yaml(spec):
                continue
            result["full_yaml_count"] += 1

            validation_result = self.hallucination_validation(spec)
            if validation_result:
                result["hallucinated_fields"].extend(validation_result.get("hallucinated", []))
                result["schema_errors"].extend(validation_result.get("errors", []))
            parsed.append(spec)

        if self.prompt.validation_mode == "yaml_baseline":
            category_results = self.yaml_category_validation(parsed)
            result["category_results"] = category_results

            for r in category_results:
                if r["status"] == "matched":
                    fields = r.get("fields_covered", "0/0")
                    matched, total = fields.split("/")
                    result["params_matched"] += int(matched)
                    result["params_total"] += int(total)
                    for field, status in r.get("field_results", {}).items():
                        if "missing" in str(status) or "expected" in str(status):
                            result["missing_params"].append(field)

            # logger.info(f"[Validation Result]:\n{yaml.safe_dump(category_results)}")

        return result

    def hallucination_validation(self, yaml_spec):
        if not self.is_full_yaml(yaml_spec):
            return None
        
        logger.info(f"Detected YAML for Kind: [{yaml_spec['kind']}]")
        logger.info(f"Validating against CRD schema for Kind: [{yaml_spec['kind']}]")
        
        result = helpers.validate_against_crd(yaml_spec)
        
        if result is None:
            return None
        
        if result["hallucinated"]:
            logger.warning(f"[Hallucinated fields]: {result['hallucinated']}")
        
        logger.info(f"[Schema validation]: {len(result['valid'])}/{result['total_fields']} fields valid")
        
        return {
            "hallucinated": result["hallucinated"],
            "errors": [f"Field not in CRD: {f}" for f in result["hallucinated"]]
        }

    def score(self, results):
        citation_recall = results["citation"]["recall"]
        yaml_r = results["yaml"]
        facts = results.get("facts", {})

        breakdown = {"citation_recall": round(citation_recall, 2)}
        actionable = {}

        if results["citation"]["missed"]:
            actionable["missed_citations"] = results["citation"]["missed"]

        if self.prompt.validation_mode == "yaml_baseline":
            # No YAML at all = fail
            if yaml_r["blocks_found"] == 0:
                return {
                    "overall": 0,
                    "breakdown": breakdown,
                    "actionable": {**actionable, "error": "no YAML generated"}
                }

            parseable = yaml_r["parseable_count"] / yaml_r["blocks_found"]
            schema_valid = 1 if not yaml_r["schema_errors"] else 0
            hallucination = 0 if yaml_r["hallucinated_fields"] else 1
            params = yaml_r["params_matched"] / yaml_r["params_total"] if yaml_r["params_total"] > 0 else 0

            overall = (
                citation_recall * 0.15 +
                parseable * 0.10 +
                schema_valid * 0.20 +
                hallucination * 0.25 +
                params * 0.30
            )

            breakdown.update({
                "yaml_parseable": round(parseable, 2),
                "schema_valid": schema_valid,          # was kubeconform_valid
                "hallucination": hallucination,
                "params": round(params, 2)
            })

            if yaml_r["hallucinated_fields"]:
                actionable["hallucinated_fields"] = yaml_r["hallucinated_fields"]
            if yaml_r["schema_errors"]:
                actionable["schema_errors"] = yaml_r["schema_errors"]
            if yaml_r["missing_params"]:
                actionable["missing_params"] = yaml_r["missing_params"]

        else:
            # rubric mode
            fact_score = facts["covered"] / facts["total"] if facts.get("total", 0) > 0 else 0

            if yaml_r["blocks_found"] > 0:
                parseable = yaml_r["parseable_count"] / yaml_r["blocks_found"]
                schema_valid = 1 if not yaml_r["schema_errors"] else 0
                hallucination = 0 if yaml_r["hallucinated_fields"] else 1

                overall = (
                    citation_recall * 0.20 +
                    fact_score * 0.40 +
                    parseable * 0.05 +
                    schema_valid * 0.15 +
                    hallucination * 0.20
                )

                breakdown.update({
                    "fact_score": round(fact_score, 2),
                    "yaml_parseable": round(parseable, 2),
                    "schema_valid": schema_valid,          # was kubeconform_valid
                    "hallucination": hallucination
                })

                if yaml_r["hallucinated_fields"]:
                    actionable["hallucinated_fields"] = yaml_r["hallucinated_fields"]
                if yaml_r["schema_errors"]:
                    actionable["schema_errors"] = yaml_r["schema_errors"]
            else:
                overall = (
                    citation_recall * 0.30 +
                    fact_score * 0.70
                )
                breakdown["fact_score"] = round(fact_score, 2)

            if facts.get("missing"):
                actionable["missing_facts"] = facts["missing"]

        return {
            "overall": round(overall, 2),
            "breakdown": breakdown,
            "actionable": actionable
        }


    def yaml_category_validation(self, parsed_yamls):
        """Reconcile every expected entry against the set of LLM yamls.
        Returns one result per expected entry (matched OR absent) plus extras."""
        expected_yamls = self.prompt.yaml_validation
        results, used_indices = [], set()

        for expected in expected_yamls:
            ek, ev = expected["expected_kind"], expected["expected_api_version"]
            candidates = [
                (i, y) for i, y in enumerate(parsed_yamls)
                if i not in used_indices and y.get("kind") == ek and y.get("apiVersion") == ev
            ]
            if not candidates:
                results.append({
                    "status": "absent",
                    "passed": False,
                    "expected_kind": ek,
                    "expected_api_version": ev,
                    "reason": f"LLM did not return a {ek} ({ev})",
                })
                continue

            scored = [(self._score_match(expected, y), i, y) for i, y in candidates]
            score, idx, picked = max(scored, key=lambda t: t[0])
            used_indices.add(idx)
            results.append(self._validate_one(expected, picked))

        for i, y in enumerate(parsed_yamls):
            if i not in used_indices:
                results.append({
                    "status": "extra",
                    "passed": True,
                    "actual_kind": y.get("kind"),
                    "actual_api_version": y.get("apiVersion"),
                    "reason": "LLM returned a YAML not listed in yaml_validation",
                })

        matched = sum(1 for r in results if r["status"] == "matched")
        logger.info(f"[YAML CRs]: {matched} / {len(expected_yamls)} expected CRs matched")
        return results

    def _score_match(self, expected, yaml_spec):
        yaml_dict = helpers.flatten_yaml(yaml_spec)
        fields = expected.get("expected_parameters") or {}
        return sum(1 for f, v in fields.items() if self._field_ok(yaml_dict, f, v))

    def _field_ok(self, yaml_dict, field, value):
        if field not in yaml_dict:
            return False
        return value == "*" or yaml_dict[field] == value

    def _validate_one(self, expected, yaml_spec):
        yaml_dict = helpers.flatten_yaml(yaml_spec)
        fields = expected.get("expected_parameters") or {}
        out = {
            "status": "matched",
            "passed": True,
            "expected_kind": expected["expected_kind"],
            "expected_api_version": expected["expected_api_version"],
            "llm_response": yaml_spec,
            "field_results": {},
        }
        covered = 0
        for field, value in fields.items():
            if field not in yaml_dict:
                out["passed"] = False
                out["field_results"][field] = f"missing (expected {value!r})"
            elif value == "*":
                out["field_results"][field] = f"present ({yaml_dict[field]!r})"
                covered += 1
            elif yaml_dict[field] != value:
                out["passed"] = False
                out["field_results"][field] = f"expected {value!r}, got {yaml_dict[field]!r}"
            else:
                out["field_results"][field] = "ok"
                covered += 1
        out["fields_covered"] = f"{covered}/{len(fields)}"
        return out

    def is_full_yaml(self, yaml_spec):
        return "apiVersion" in yaml_spec and "kind" in yaml_spec and \
            "metadata" in yaml_spec and "name" in yaml_spec["metadata"]

    def yaml_extractor(self):
        yaml_pattern = r'```ya?ml([\s\S]*?)```'
        return re.findall(yaml_pattern, self.ols_response)
